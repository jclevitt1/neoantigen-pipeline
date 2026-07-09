"""
Stage 2a — Somatic variant calling ("the diff").  (adapter; contract + orchestration)

Tumor DNA MINUS normal DNA -> mutations unique to the cancer, annotated with
protein consequences. The concrete caller+annotator lives under an approach subdir
(mutect2_vep/). See stages/variants/README.md for the concept.

NOTE: 2a and 2b are two INDEPENDENT branches off the normalized BAMs — separate
stages precisely so the DAG can run them in parallel later. 2a reads tumor+normal.
"""
from __future__ import annotations

from core import Stage
from .. import checks


class VariantCallStage(Stage):
    name = "2a-variants"
    description = "The 'diff': somatic variants (tumor - normal), annotated with protein consequences."

    def __init__(self, case):
        self.case = case

    @property
    def inputs(self):
        c = self.case
        return [c.tumor_dna_bam, c.normal_dna_bam, c.reference]

    @property
    def outputs(self):
        return [self.case.somatic_vcf]

    def dry_check_inputs(self) -> None:
        checks.require_bgzf(self.case.tumor_dna_bam)
        checks.require_bgzf(self.case.normal_dna_bam)
        checks.require_nonempty(self.case.reference)

    def dry_check_outputs(self) -> None:
        checks.require_vcf(self.case.somatic_vcf)
        # TODO: also assert the VCF header advertises CSQ/ANN (annotation present)

    def run(self) -> None:
        raise NotImplementedError("2a-variants.run — Mutect2 + VEP annotate (TODO)")
