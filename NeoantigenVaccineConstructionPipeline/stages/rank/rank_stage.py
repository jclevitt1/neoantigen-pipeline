"""
Stage 4 — Rank.  (NATIVE; contract + orchestration)

candidate peptides + HLA alleles -> MHC binding + immunogenicity scores, sorted.
This is the differentiated core. The scoring itself is pluggable: this stage owns
the file I/O and delegates to a `Ranker` (base.py + the approach subdirs). The
default is the logistic TME model — a documented filler, swappable without
touching this Stage. See stages/rank/README.md.
"""
from __future__ import annotations

import csv
import json

from core import Stage
from .. import checks
from .base import Ranker
from . import DEFAULT_RANKER

_SCORE_COLS = ["peptide", *Ranker.SCORE_COLUMNS]


def _read_alleles(hla_json_path) -> list[str]:
    """hla.json may be {'alleles': [...]} or a bare list — accept both."""
    with open(hla_json_path) as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        return list(data.get("alleles", []))
    return list(data)


class RankStage(Stage):
    name = "4-rank"
    kind = "native"
    description = "Score peptides by MHC binding + immunogenicity (pluggable ranker; default: logistic TME)."

    def __init__(self, case, ranker: Ranker | None = None):
        self.case = case
        self.ranker = ranker or DEFAULT_RANKER()
        # Let a ranker load anything it needs from the Case once (e.g. the
        # composite ranker reads the proteome for dissimilarity-to-self).
        self.ranker.configure(case)

    @property
    def inputs(self):
        c = self.case
        # A ranker may add DAG edges (files it reads); e.g. the composite ranker
        # depends on the proteome. Mirrors how CandidateStage wires expression.
        return [c.candidates_tsv, c.hla_json, *self.ranker.required_inputs(c)]

    @property
    def outputs(self):
        return [self.case.ranked_tsv]

    def dry_check_inputs(self) -> None:
        checks.require_tsv_columns(self.case.candidates_tsv, ["peptide"])
        checks.require_json(self.case.hla_json)

    def dry_check_outputs(self) -> None:
        checks.require_tsv_columns(self.case.ranked_tsv, _SCORE_COLS)

    def self_test(self) -> str | None:
        # Assert the pure Axis-2 recognition math the default ranker rests on.
        # (The MHCflurry binding calls need the wet package + Colab, so they're
        # exercised there; the math below is deterministic and runs anywhere.)
        from .mhcflurry import recognition as rec
        try:
            # agretopicity = Kd_WT / Kd_MT: mutant binding 10x stronger (10 vs 100 nM)
            assert rec.agretopicity(10.0, 100.0) == 10.0
            assert rec.agretopicity(None, 100.0) is None          # missing → None
            # dissimilarity-to-self: verbatim self = 0.0, novel = 1.0
            assert rec.dissimilarity_to_self("SIINFEKL", "AAASIINFEKLAAA") == 0.0
            assert rec.dissimilarity_to_self("WWWWWWWW", "AAASIINFEKLAAA") == 1.0
            assert rec.dissimilarity_to_self("ABC", "") is None    # no proteome → None
            # Luksza composite Q = R·D, D = log A + log C. With C=1, R=1 (dormant):
            # Q = log(agretopicity). Higher agretopicity → higher quality.
            q_hi = rec.luksza_quality(10.0, 1.0)
            q_lo = rec.luksza_quality(2.0, 1.0)
            assert q_hi > q_lo > 0
            assert rec.luksza_quality(None) is None
            # A novel peptide (C=1) must outrank an identical-agretopicity self one (C≈0)
            assert rec.luksza_quality(5.0, 1.0) > rec.luksza_quality(5.0, 0.0)
        except AssertionError as e:  # noqa: BLE001
            return f"4-rank self_test failed: {e}"
        return None

    def run(self) -> None:
        c = self.case
        with open(c.candidates_tsv, newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        alleles = _read_alleles(c.hla_json)

        scored = self.ranker.score(rows, alleles)

        # Union of all keys, contract columns first, extras (features) after.
        extras = [k for k in (scored[0].keys() if scored else []) if k not in _SCORE_COLS]
        fieldnames = _SCORE_COLS + extras
        with open(c.ranked_tsv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
            w.writeheader()
            w.writerows(scored)
