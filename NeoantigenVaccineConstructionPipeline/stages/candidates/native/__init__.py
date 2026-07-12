"""
native — stage 3 approach: generate candidate peptides ourselves (no pVACseq).

`windows.py` is the pure heart (mutant protein -> covering k-mers); `vcf.py`
parses the VEP-annotated VCF into variant dicts; `expression.py` is the
pluggable TPM tag. This is the "we own it" approach, fully testable on fixtures.
"""
from . import windows, vcf
from .expression import (
    ExpressionSource, PlaceholderExpression, FeatureCountsExpression,
    DEFAULT_EXPRESSION, UNKNOWN_TPM,
)

__all__ = [
    "windows", "vcf",
    "ExpressionSource", "PlaceholderExpression", "FeatureCountsExpression",
    "DEFAULT_EXPRESSION", "UNKNOWN_TPM",
]
