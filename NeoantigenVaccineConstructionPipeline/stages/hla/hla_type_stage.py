"""
Stage 2b — HLA typing.  (adapter; contract + orchestration)

Read the patient's own MHC-I alleles from the NORMAL sample. The concrete typer
lives under an approach subdir (optitype/). See stages/hla/README.md.

NOTE: independent branch of stage 2 (see 2a note) — reads normal DNA only.
"""
from __future__ import annotations

from core import Stage
from .. import checks


class HlaTypeStage(Stage):
    name = "2b-hla"
    description = "Type the patient's MHC-I alleles (HLA-A/B/C) from the normal sample."

    def __init__(self, case):
        self.case = case

    @property
    def inputs(self):
        return [self.case.normal_dna_bam]

    @property
    def outputs(self):
        return [self.case.hla_json]

    def dry_check_inputs(self) -> None:
        checks.require_bgzf(self.case.normal_dna_bam)

    def dry_check_outputs(self) -> None:
        checks.require_json(self.case.hla_json)
        # TODO: assert it contains HLA-A/-B/-C alleles in standard nomenclature

    def run(self) -> None:
        raise NotImplementedError("2b-hla.run — OptiType/arcasHLA typing (TODO)")
