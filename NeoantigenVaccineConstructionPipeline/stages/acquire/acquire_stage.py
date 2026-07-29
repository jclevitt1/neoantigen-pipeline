"""
Stage 0 — Acquire.  (contract + orchestration)

Make the Case's three raw sample files exist, then hand off to stage 1 (normalize).
The *how* is pluggable via an `AcquireSource` (base.py): files already on disk, or
region-sliced from a remote source. Sits before 1-input in the DAG:

    0-acquire -> 1-input -> 2a/2b -> ...

Because SEQC2 ships ALIGNED BAMs, the slice source produces aligned BAMs directly,
so stage 1 is a light sort/index passthrough for the MVP (no bwa/STAR run).
See stages/acquire/README.md.
"""
from __future__ import annotations

from core import Stage
from .. import checks
from . import DEFAULT_SOURCE
from .base import AcquireSource


class AcquireStage(Stage):
    """Stage 0 - stage the three raw sample files (tumor DNA, normal DNA, tumor RNA)
    into the case workdir: either verify on-disk copies or region-slice them out of
    a remote archive, so nothing downstream has to know where the data came from."""
    name = "0-acquire"
    kind = "adapter"
    description = "Stage the three raw sample files (on-disk, or region-sliced from a remote source)."

    def __init__(self, case, source: AcquireSource | None = None):
        self.case = case
        self.source = source or DEFAULT_SOURCE()

    @property
    def inputs(self):
        return []  # external roots are remote/pre-staged, not pipeline files

    @property
    def outputs(self):
        c = self.case
        return [c.tumor_dna, c.normal_dna, c.tumor_rna]

    def dry_check_outputs(self) -> None:
        for p in self.outputs:
            checks.require_nonempty(p)
            checks.require_bgzf(p)  # SEQC2 slices are BAMs (BGZF)

    def run(self) -> None:
        self.source.ensure(self.case)
