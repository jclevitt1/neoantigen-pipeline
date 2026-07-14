"""
binding.py — the Axis-1 (presentation) engine: a thin MHCflurry 2.0 wrapper.

This is the ONE wet dependency in stage 4. MHCflurry is imported lazily (inside
methods, never at module load) for three reasons:
  1. the rest of stage 4 — the Ranker interface, the recognition math, the
     self-tests — must import and run WITHOUT the package (e.g. on a laptop);
  2. `pip install mhcflurry` + `mhcflurry-downloads fetch` only happens in the
     Colab runtime where the pipeline actually executes;
  3. importing mhcflurry pulls in TensorFlow, which is slow and heavy.

Why MHCflurry 2.0 (see docs/ranking_methodology.md §3): it is the only presentation
predictor that is free, Apache-2.0 (redistributable), pip-installable, and runs
fully offline in Colab. It outputs an eluted-ligand PRESENTATION score (0–1), not
just an IC50, and its presentation head is itself a logistic regression over
(affinity, processing) trained on mass-spec — a professionally-trained version of
the homegrown model this replaces.
"""
from __future__ import annotations


def _normalize_allele(a: str) -> str:
    """Coerce an HLA call to MHCflurry's expected 'HLA-A*02:01' form."""
    a = a.strip()
    if not a:
        return a
    return a if a.upper().startswith("HLA-") else f"HLA-{a}"


class MhcflurryBinder:
    """Loads the MHCflurry Class1 presentation predictor once, then scores
    peptides. Instantiating does NOT load the model (so importing/constructing is
    cheap); the model loads on first prediction call."""

    def __init__(self):
        self._predictor = None

    def _load(self):
        if self._predictor is None:
            from mhcflurry import Class1PresentationPredictor  # lazy: Colab-only
            self._predictor = Class1PresentationPredictor.load()
        return self._predictor

    def supported_alleles(self, alleles: list[str]) -> list[str]:
        """Keep only alleles MHCflurry actually models (unknown alleles raise)."""
        pred = self._load()
        supported = set(getattr(pred, "supported_alleles", []) or [])
        norm = [_normalize_allele(a) for a in alleles]
        if not supported:
            return [a for a in norm if a]
        return [a for a in norm if a in supported]

    def best_presentation(self, peptides: list[str], alleles: list[str]) -> dict:
        """For each peptide, the BEST allele's presentation across the patient's
        alleles. Returns {peptide: {best_allele, presentation_score,
        processing_score, affinity}}. `affinity` is nM (lower = stronger); it
        feeds agretopicity. Empty dict if nothing is scoreable."""
        peptides = [p for p in dict.fromkeys(peptides) if p]  # dedup, keep order
        alleles = self.supported_alleles(alleles)
        if not peptides or not alleles:
            return {}
        pred = self._load()
        # A flat allele list = one sample; predict() returns the best allele per
        # peptide with affinity + processing + presentation columns.
        df = pred.predict(peptides=peptides, alleles=alleles,
                          include_affinity_percentile=True)
        out: dict[str, dict] = {}
        for row in df.to_dict("records"):
            out[row["peptide"]] = {
                "best_allele": row.get("best_allele", ""),
                "presentation_score": _get(row, "presentation_score"),
                "processing_score": _get(row, "processing_score"),
                "affinity": _get(row, "affinity"),
            }
        return out

    def affinity_for(self, peptides: list[str], allele: str) -> dict:
        """Affinity (nM) of each peptide for ONE specific allele. Used to score
        the WILD-TYPE counterpart at the mutant's best allele, so agretopicity
        compares like with like. Returns {peptide: affinity_nM}."""
        allele = _normalize_allele(allele)
        peptides = [p for p in dict.fromkeys(peptides) if p]
        if not peptides or not allele:
            return {}
        pred = self._load()
        if allele not in set(getattr(pred, "supported_alleles", []) or [allele]):
            return {}
        df = pred.predict(peptides=peptides, alleles=[allele])
        return {row["peptide"]: _get(row, "affinity") for row in df.to_dict("records")}


def _get(row: dict, key: str):
    """Pull a numeric column if MHCflurry emitted it (schema varies by version)."""
    v = row.get(key)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
