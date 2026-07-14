"""
Stage 5 — Eval filters.  (NATIVE; contract + orchestration)

ranked peptides -> pass/fail flags. GATES stage 6: this stage only *flags*; it
does not drop rows. Construct (stage 6) builds from the survivors. The filter
logic lives in the rule_based/ approach; this Stage orchestrates it over the file.
See stages/eval/README.md.
"""
from __future__ import annotations

import csv

from core import Stage
from .. import checks
from .rule_based import filters

_FLAG_COLS = ["peptide", "autoimmunity_flag", "clonality", "manufacturability"]


class EvalStage(Stage):
    name = "5-eval"
    kind = "native"
    description = "Filter peptides: autoimmunity, clonality, manufacturability. Gates the construct."

    def __init__(self, case):
        self.case = case

    @property
    def inputs(self):
        # proteome is an external root for the self-similarity check
        return [self.case.ranked_tsv, self.case.proteome]

    @property
    def outputs(self):
        return [self.case.filtered_tsv]

    def dry_check_inputs(self) -> None:
        checks.require_tsv_columns(self.case.ranked_tsv, ["peptide"])
        checks.require_fasta(self.case.proteome)

    def dry_check_outputs(self) -> None:
        checks.require_tsv_columns(self.case.filtered_tsv, _FLAG_COLS)

    def self_test(self) -> str | None:
        try:
            assert filters.classify_clonality(0.95) == "clonal"
            assert filters.classify_clonality(0.30) == "subclonal"
            assert filters.classify_clonality("") == "unknown"
            assert filters.check_manufacturability("SIINFEKL") == "pass"     # benign
            assert filters.check_manufacturability("IIIIIIIII") == "fail"    # hydrophobic
            assert filters.check_manufacturability("CCADEFGHI") == "fail"    # 2 cysteines
            idx = filters.proteome_index_from_str(">p1\nAAASIINFEKLAAA\n")
            assert filters.flag_autoimmunity("SIINFEKL", idx) is True        # self
            assert filters.flag_autoimmunity("WWWWWWWW", idx) is False       # novel
        except AssertionError as e:  # noqa: BLE001
            return f"5-eval self_test failed: {e}"
        return None

    def run(self) -> None:
        c = self.case
        proteome_index = filters.load_proteome_index(c.proteome)

        with open(c.ranked_tsv, newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))

        out_rows = []
        for r in rows:
            pep = r.get("peptide", "")
            ccf = r.get("ccf", r.get("vaf"))
            out = dict(r)
            out["autoimmunity_flag"] = filters.flag_autoimmunity(pep, proteome_index)
            out["clonality"] = filters.classify_clonality(ccf)
            out["manufacturability"] = filters.check_manufacturability(pep)
            out_rows.append(out)

        extras = [k for k in (out_rows[0].keys() if out_rows else []) if k not in _FLAG_COLS]
        fieldnames = _FLAG_COLS + extras
        with open(c.filtered_tsv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
            w.writeheader()
            w.writerows(out_rows)
