"""
MHCflurry-backed rankers — the modernized stage-4 scoring.

Two implementations behind the same `Ranker` seam, matching the upgrade path in
docs/ranking_methodology.md:

  - MhcflurryPresentationRanker  (Axis 1 only)  — the smallest drop-in: replace
    the homegrown logistic regression with MHCflurry's eluted-ligand presentation
    score. Orders purely by "will it be displayed?".

  - LukszaCompositeRanker  (Axis 1 gate + Axis 2 composite)  — the default. GATES
    on presentation + expression (TESLA's core finding: recognition features are
    meaningless on un-presented peptides), then ranks the survivors by the Luksza
    quality composite Q = R·D over agretopicity (DAI), dissimilarity-to-self, and
    (optionally) foreignness. Flags rather than drops, mirroring stage 5.

Both keep the stable contract columns (`binding_affinity`, `immunogenicity`) and
emit their richer features as extra columns the Stage passes straight through.
"""
from __future__ import annotations

from ..base import Ranker
from . import recognition as rec
from .binding import MhcflurryBinder

_NEG_INF = float("-inf")


class MhcflurryPresentationRanker(Ranker):
    """Rank by MHCflurry 2.0 presentation score alone - Axis 1 only, no recognition
    modelling and no tunables. The simplest defensible ranker, and a useful control
    for whether the recognition composite is adding anything."""
    name = "mhcflurry-presentation"
    description = ("Axis 1 only: order by MHCflurry 2.0 eluted-ligand presentation "
                   "score. Drop-in replacement for the logistic filler.")

    def __init__(self, binder: MhcflurryBinder | None = None):
        self.binder = binder or MhcflurryBinder()

    def score(self, rows: list[dict], alleles: list[str]) -> list[dict]:
        best = self.binder.best_presentation([r.get("peptide", "") for r in rows], alleles)
        scored = []
        for r in rows:
            info = best.get(r.get("peptide", ""), {})
            out = dict(r)
            out["best_allele"] = info.get("best_allele", "")
            out["presentation_score"] = _round(info.get("presentation_score"))
            out["processing_score"] = _round(info.get("processing_score"))
            out["binding_affinity"] = _round(info.get("affinity"))
            # This ranker has no recognition model — presentation IS the sort key.
            # The composite ranker replaces this with a real Axis-2 score.
            out["immunogenicity"] = out["presentation_score"] if out["presentation_score"] != "" else ""
            scored.append(out)
        scored.sort(key=lambda x: _key(x["immunogenicity"]), reverse=True)
        return scored


class LukszaCompositeRanker(Ranker):
    """Gate on MHCflurry presentation, then rank the survivors by a Luksza-style
    recognition composite (agretopicity, dissimilarity-to-self, foreignness). Gating
    first because recognition features are meaningless on peptides that are never
    presented. The current default."""
    name = "luksza-composite"
    description = ("Gate on MHCflurry presentation + expression, then rank survivors "
                   "by the Luksza quality composite (agretopicity × dissimilarity-to-self).")

    # Gate thresholds (see docs/ranking_methodology.md §1, §5).
    PRESENT_MIN = 0.7   # MHCflurry presentation_score at/above this = "presented"

    def __init__(self, binder: MhcflurryBinder | None = None,
                 iedb_epitopes: list[str] | None = None):
        self.binder = binder or MhcflurryBinder()
        self.iedb_epitopes = iedb_epitopes  # None → foreignness term stays dormant
        self._proteome_index: str | None = None

    # --- seam wiring: the composite needs the proteome for dissimilarity-to-self.
    def required_inputs(self, case) -> list:
        return [case.proteome]

    def configure(self, case) -> None:
        # Loaded once here rather than per-score so the DAG edge (required_inputs)
        # and the data load stay in lock-step. Tolerate a missing proteome — the
        # term simply drops out (dissimilarity → None → C defaults to 1.0).
        try:
            self._proteome_index = rec.load_proteome_index(case.proteome)
        except (OSError, ValueError):
            self._proteome_index = None

    def score(self, rows: list[dict], alleles: list[str]) -> list[dict]:
        peptides = [r.get("peptide", "") for r in rows]
        best = self.binder.best_presentation(peptides, alleles)

        # Score each wild-type counterpart at ITS mutant's best allele, so
        # agretopicity compares like allele with like. Batch by allele.
        wt_by_allele: dict[str, set] = {}
        for r in rows:
            info = best.get(r.get("peptide", ""))
            wt = r.get("wt_peptide", "")
            if info and wt and info.get("best_allele"):
                wt_by_allele.setdefault(info["best_allele"], set()).add(wt)
        wt_aff: dict[str, dict] = {
            allele: self.binder.affinity_for(list(peps), allele)
            for allele, peps in wt_by_allele.items()
        }

        scored = []
        for r in rows:
            out = dict(r)
            pep = r.get("peptide", "")
            info = best.get(pep, {})
            pres = _num(info.get("presentation_score"))
            mut_aff = _num(info.get("affinity"))
            allele = info.get("best_allele", "")

            out["best_allele"] = allele
            out["presentation_score"] = _round(pres)
            out["binding_affinity"] = _round(mut_aff)

            tier = self._gate(pres, r.get("tpm"))
            out["tier"] = tier
            if tier != "pass":
                # gated out: keep the row (stage 5 may still want it), no rank score
                out["agretopicity"] = ""
                out["dissimilarity_to_self"] = ""
                out["immunogenicity"] = ""
                scored.append(out)
                continue

            wt = r.get("wt_peptide", "")
            wt_a = _num(wt_aff.get(allele, {}).get(wt)) if wt else None
            dai = rec.agretopicity(mut_aff, wt_a)
            dissim = rec.dissimilarity_to_self(pep, self._proteome_index)
            foreign = rec.foreignness(pep, self.iedb_epitopes) if self.iedb_epitopes else None
            q = rec.luksza_quality(dai, dissim, foreign)

            out["agretopicity"] = _round(dai)
            out["dissimilarity_to_self"] = _round(dissim)
            out["immunogenicity"] = _round(q)
            scored.append(out)

        # Presented-and-ranked first (by Q desc); gated-out rows sink to the bottom.
        scored.sort(key=lambda x: _key(x["immunogenicity"]), reverse=True)
        return scored

    def _gate(self, presentation, tpm) -> str:
        """TESLA presentation-first gate. Returns a pVACseq-style tier label."""
        if presentation is None:
            return "no-binding"
        if presentation < self.PRESENT_MIN:
            return "low-presentation"
        # expression: unknown (placeholder) survives; a REAL zero does not.
        t = _num(tpm)
        if t is not None and t <= 0:
            return "no-expression"
        return "pass"


# --------------------------------------------------------------------------- #
def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _round(v):
    return round(float(v), 6) if _num(v) is not None else ""


def _key(v):
    """Sort key: numeric best-first, blanks (gated-out) sink to the bottom."""
    n = _num(v)
    return n if n is not None else _NEG_INF
