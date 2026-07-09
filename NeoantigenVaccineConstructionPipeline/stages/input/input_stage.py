"""
Stage 1 — Input / Normalize.  (adapter; contract + orchestration)

Maps whatever the public source gave us -> three normalized BAMs. The concrete
alignment approach lives under an approach subdir (align_bwa_star/). See
stages/input/README.md for the concept.
"""
from __future__ import annotations

from core import Stage
from .. import checks

_RAW_EXTS = [".bam", ".cram", ".fastq", ".fq", ".fastq.gz", ".fq.gz", ".sra"]


class InputStage(Stage):
    name = "1-input"
    description = "Normalize raw sequencing (FASTQ/BAM/CRAM) into three aligned BAMs."

    def __init__(self, case):
        self.case = case

    @property
    def inputs(self):
        c = self.case
        return [c.tumor_dna, c.normal_dna, c.tumor_rna]

    @property
    def outputs(self):
        c = self.case
        return [c.tumor_dna_bam, c.normal_dna_bam, c.tumor_rna_bam]

    def dry_check_inputs(self) -> None:
        for p in self.inputs:
            checks.require_nonempty(p)
            checks.require_ext(p, _RAW_EXTS)

    def dry_check_outputs(self) -> None:
        for p in self.outputs:
            checks.require_nonempty(p)
            checks.require_bgzf(p)  # TODO: also require a .bai index alongside

    def run(self) -> None:
        raise NotImplementedError("1-input.run — normalize raw -> BAM x3 (TODO)")
