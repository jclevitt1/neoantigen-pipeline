"""
Stage 6 — Construct.  (contract + orchestration)

Top surviving peptides (post stage-5 gate) -> one vaccine construct: peptides
concatenated with linkers, then reverse-translated (codon-optimized). Runs AFTER
stage 5 (consumes filtered.tsv), so in the DAG the arrows are 4 -> 5 -> 6.
Writes the construct FASTA (amino-acid + nucleotide records) + a JSON recipe for
reproducibility. Assembly logic lives in the string_of_beads/ approach.
See stages/construct/README.md.
"""
from __future__ import annotations

import csv
import json

from core import Stage
from .. import checks
from .string_of_beads import builder


class ConstructStage(Stage):
    name = "6-construct"
    kind = "native"
    description = "Assemble surviving peptides (+linkers, codon-optimized) into a vaccine construct."

    def __init__(self, case):
        self.case = case

    @property
    def inputs(self):
        return [self.case.filtered_tsv]

    @property
    def outputs(self):
        c = self.case
        return [c.construct_fasta, c.construct_json]

    def dry_check_inputs(self) -> None:
        checks.require_tsv_columns(self.case.filtered_tsv, ["peptide"])

    def dry_check_outputs(self) -> None:
        checks.require_fasta(self.case.construct_fasta)
        checks.require_json(self.case.construct_json)

    def self_test(self) -> str | None:
        try:
            rows = [
                {"peptide": "SIINFEKL", "immunogenicity": "0.9",
                 "autoimmunity_flag": "False", "manufacturability": "pass", "clonality": "clonal"},
                {"peptide": "YTNVGWLMK", "immunogenicity": "0.8",
                 "autoimmunity_flag": "False", "manufacturability": "pass", "clonality": "subclonal"},
                {"peptide": "DANGERSELF", "immunogenicity": "0.99",   # highest score but...
                 "autoimmunity_flag": "True", "manufacturability": "pass", "clonality": "clonal"},
                {"peptide": "IIIIIIIII", "immunogenicity": "0.95",    # ...and this fails manuf
                 "autoimmunity_flag": "False", "manufacturability": "fail", "clonality": "clonal"},
                {"peptide": "GATEDLOWP", "immunogenicity": "0.97",   # clean + top score, but...
                 "autoimmunity_flag": "False", "manufacturability": "pass", "clonality": "clonal",
                 "tier": "low-presentation"},                        # ...gated out on presentation
            ]
            rec = builder.build_construct(rows)
            # only the two safe/manufacturable/PRESENTED survivors, best-first
            # (GATEDLOWP outscores both but never got presented -> excluded)
            assert rec["peptides"] == ["SIINFEKL", "YTNVGWLMK"], rec["peptides"]
            assert rec["construct_aa"] == "SIINFEKLAAYYTNVGWLMK", rec["construct_aa"]
            # nucleotide length = 3 * amino-acid length
            assert len(rec["construct_nt"]) == 3 * len(rec["construct_aa"])
        except AssertionError as e:  # noqa: BLE001
            return f"6-construct self_test failed: {e}"
        return None

    def run(self) -> None:
        c = self.case
        with open(c.filtered_tsv, newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))

        rec = builder.build_construct(rows)

        with open(c.construct_fasta, "w") as fh:
            fh.write(f">{c.sample_id}_construct_aa peptides={rec['n_peptides']} linker={rec['linker']}\n")
            fh.write(rec["construct_aa"] + "\n")
            fh.write(f">{c.sample_id}_construct_nt codon_table={rec['codon_table']}\n")
            fh.write(rec["construct_nt"] + "\n")

        with open(c.construct_json, "w") as fh:
            json.dump(rec, fh, indent=2)
