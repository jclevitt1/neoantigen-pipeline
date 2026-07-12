"""align_bwa_star — stage 1 approach: bwa (DNA) + STAR (RNA) + samtools sort/index.

The routing/parsing (plan.py) is real and tested; the tool execution defers to Colab.
"""
from .plan import (
    Step, classify, normalization_plan,
    parse_sam_header, needs_sort, contig_style,
)

__all__ = ["Step", "classify", "normalization_plan",
           "parse_sam_header", "needs_sort", "contig_style"]
