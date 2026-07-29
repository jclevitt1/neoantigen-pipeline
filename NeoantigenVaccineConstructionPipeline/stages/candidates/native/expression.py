"""
expression.py — the pluggable expression tag for stage 3.

A candidate peptide only matters if its gene is actually transcribed in the
tumor. Real TPM comes from the tumor RNA BAM via a quantifier
(Salmon / RSEM / featureCounts). RNA is deferred (still FASTQ needing STAR), so
this is a seam, exactly like `Ranker` (stage 4) and `AcquireSource` (stage 0):

  - `PlaceholderExpression` (default) needs no RNA — emits tpm='NA' and keeps
    every row. It NEVER drops (we can't know expression, so we don't guess).
  - `FeatureCountsExpression` (stub) is the real one; it declares the RNA BAM as
    a required input, so wiring it in makes stage 3's DAG dependency real.

The source both provides `tpm_for(...)` AND declares `required_inputs(case)`, so
`CandidateStage.inputs` stays honest: placeholder -> just the VCF (runs today);
real source -> VCF + RNA BAM.
"""
from __future__ import annotations

from abc import abstractmethod

from core import Strategy

#: sentinel written when expression is unknown (placeholder path)
UNKNOWN_TPM = "NA"


class ExpressionSource(Strategy):
    """Seam: where per-gene expression (TPM) comes from when tagging candidate peptides.
    A mutation in a silent gene makes no protein, so there is nothing to present."""
    @abstractmethod
    def tpm_for(self, gene: str, transcript: str) -> str | float:
        """TPM for a gene/transcript, or UNKNOWN_TPM if not determinable."""

    def required_inputs(self, case) -> list:
        """Extra Case files this source needs (declared into the stage's inputs)."""
        return []

    def dry_check(self, case) -> None:
        """Cheap validation of this source's inputs. Override if any."""


class PlaceholderExpression(ExpressionSource):
    """Default: no RNA available yet. Every candidate gets tpm='NA' and survives.

    Honest MVP behaviour — the alternative (dropping everything, or inventing a
    number) is worse. When RNA lands, swap in FeatureCountsExpression.
    """

    def tpm_for(self, gene: str, transcript: str) -> str:
        return UNKNOWN_TPM


class FeatureCountsExpression(ExpressionSource):
    """Real expression from the tumor RNA BAM (planned).

    Would quantify TPM per gene/transcript over `case.tumor_rna_bam` and look it
    up here. Declares the RNA BAM as a required input so the DAG orders 1-input
    before 3-candidates for real.
    """

    def __init__(self, tpm_min: float = 1.0):
        self.tpm_min = tpm_min  # drop candidates below this once TPM is real

    def tpm_for(self, gene: str, transcript: str) -> str | float:
        raise NotImplementedError("FeatureCountsExpression — quantify RNA BAM (TODO, needs STAR-aligned RNA)")

    def required_inputs(self, case) -> list:
        return [case.tumor_rna_bam]

    def dry_check(self, case) -> None:
        from ... import checks
        checks.require_bgzf(case.tumor_rna_bam)


DEFAULT_EXPRESSION = PlaceholderExpression
