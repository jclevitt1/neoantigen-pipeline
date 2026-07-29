"""
Stage 2b — HLA typing.  (contract + orchestration; pluggable typer)

Read the patient's own MHC-I alleles from the NORMAL sample, so stage 4 knows
which molecules present the peptides. The concrete typer is a pluggable seam
(base.py): default `KnownGenotypeTyper` (published cell-line genotype, no reads —
runs today); `OptiTypeTyper` types from the normal BAM. See stages/hla/README.md.

NOTE: independent branch of stage 2 (see 2a note) — reads normal DNA only.
"""
from __future__ import annotations

import json

from core import Stage
from .. import checks
from .base import validate_alleles
from .known.typer import KnownGenotypeTyper

DEFAULT_TYPER = KnownGenotypeTyper


class HlaTypeStage(Stage):
    """Stage 2b - determine the patient's MHC class-I genotype (HLA-A/B/C). This is the
    restriction set every downstream binding prediction is scored against; get it
    wrong and every peptide score is wrong."""
    name = "2b-hla"
    kind = "adapter"
    description = "Type the patient's MHC-I alleles (HLA-A/B/C) from the normal sample."

    def __init__(self, case, typer=None):
        self.case = case
        # pluggable typer; default needs no reads (published genotype lookup)
        self.typer = typer or DEFAULT_TYPER()

    @property
    def inputs(self):
        # the typer declares whether it needs the normal BAM (OptiType) or not (known)
        return list(self.typer.required_inputs(self.case))

    @property
    def outputs(self):
        return [self.case.hla_json]

    def dry_check_inputs(self) -> None:
        self.typer.dry_check(self.case)

    def dry_check_outputs(self) -> None:
        checks.require_json(self.case.hla_json)
        data = json.loads(self.case.hla_json.read_text())
        validate_alleles(data.get("alleles", []))

    def self_test(self) -> str | None:
        try:
            from .base import is_valid_allele
            from .known.typer import KNOWN_GENOTYPES
            from .optitype.typer import parse_optitype_tsv

            # --- nomenclature validation ---
            assert is_valid_allele("HLA-A*29:02")
            assert not is_valid_allele("A*29:02")       # missing HLA- prefix
            assert not is_valid_allele("HLA-A*2902")    # missing field colon
            assert not is_valid_allele("HLA-Z*01:01")   # not a class-I gene

            # --- known genotype is real + well-formed ---
            hcc = KNOWN_GENOTYPES["HCC1395"]
            assert "HLA-A*29:02" in hcc and len(hcc) == 5  # A homozygous -> 5 distinct
            assert all(is_valid_allele(a) for a in hcc)

            # --- OptiType parser: collapses homozygous A, normalizes to HLA- ---
            fixture = (
                "\tA1\tA2\tB1\tB2\tC1\tC2\tReads\tObjective\n"
                "0\tA*29:02\tA*29:02\tB*08:01\tB*45:01\tC*06:02\tC*07:01\t2891\t2743.0\n"
            )
            parsed = parse_optitype_tsv(fixture)
            assert parsed == hcc, parsed  # parser output matches the published genotype
        except AssertionError as e:  # noqa: BLE001
            return f"2b-hla self_test failed: {e}"
        return None

    def run(self) -> None:
        c = self.case
        alleles = self.typer.type(c)
        validate_alleles(alleles)
        payload = {
            "sample_id": c.sample_id,
            "alleles": alleles,
            "source": type(self.typer).__name__,
        }
        c.hla_json.write_text(json.dumps(payload, indent=2) + "\n")
