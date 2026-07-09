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

    @property
    def inputs(self):
        c = self.case
        return [c.candidates_tsv, c.hla_json]

    @property
    def outputs(self):
        return [self.case.ranked_tsv]

    def dry_check_inputs(self) -> None:
        checks.require_tsv_columns(self.case.candidates_tsv, ["peptide"])
        checks.require_json(self.case.hla_json)

    def dry_check_outputs(self) -> None:
        checks.require_tsv_columns(self.case.ranked_tsv, _SCORE_COLS)

    def self_test(self) -> str | None:
        # NATIVE stage: real assertions on a fixture go here (Model A/B ranking).
        # TODO: tiny candidates.tsv + hla.json -> assert score columns + ordering.
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
