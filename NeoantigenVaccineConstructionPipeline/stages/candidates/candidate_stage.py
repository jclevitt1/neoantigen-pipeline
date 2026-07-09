"""
Stage 3 — Candidate generation.  (adapter; contract + orchestration)

Annotated somatic VCF -> mutant peptide windows (8-11mers), each tagged with RNA
expression so silent mutations drop out. The concrete generator lives under an
approach subdir (pvacseq/). See stages/candidates/README.md.
"""
from __future__ import annotations

from core import Stage
from .. import checks

_REQUIRED_COLS = ["peptide", "tpm"]  # minimal contract; more added by later stages


class CandidateStage(Stage):
    name = "3-candidates"
    description = "Translate mutations into mutant peptides (8-11mers), tagged with RNA expression."

    def __init__(self, case):
        self.case = case

    @property
    def inputs(self):
        c = self.case
        return [c.somatic_vcf, c.tumor_rna_bam]

    @property
    def outputs(self):
        return [self.case.candidates_tsv]

    def dry_check_inputs(self) -> None:
        checks.require_vcf(self.case.somatic_vcf)
        checks.require_bgzf(self.case.tumor_rna_bam)

    def dry_check_outputs(self) -> None:
        checks.require_tsv_columns(self.case.candidates_tsv, _REQUIRED_COLS)

    def run(self) -> None:
        raise NotImplementedError("3-candidates.run — pVACseq + expression tag (TODO)")
