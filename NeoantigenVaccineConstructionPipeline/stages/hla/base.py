"""
base.py — the pluggable HLA typer seam for stage 2b (like `Ranker`/`AcquireSource`).

A `HlaTyper` turns a Case into the patient's MHC-I alleles. Two live approaches:
`known/` (published genotype by sample_id — needs no reads, runs today) and
`optitype/` (real typing from the normal BAM — tool run deferred, parser real).
The typer declares its own required inputs so the stage's DAG dependency stays
honest: known -> none; OptiType -> the normal DNA BAM.
"""
from __future__ import annotations

import re
from abc import abstractmethod

from core import Strategy

# HLA class I two-field allele, e.g. 'HLA-A*02:01'. Classical class I genes: A/B/C.
# Two fields (allele group : specific protein) is the resolution binding
# predictors consume; deeper fields (:synonymous, :intronic) don't change protein.
ALLELE_RE = re.compile(r"^HLA-[ABC]\*\d{2,3}:\d{2,3}$")


def is_valid_allele(a: str) -> bool:
    return bool(ALLELE_RE.match(a))


def validate_alleles(alleles) -> None:
    """Raise unless `alleles` is a non-empty list of well-formed class-I alleles."""
    if not alleles:
        raise ValueError("no HLA alleles produced")
    bad = [a for a in alleles if not is_valid_allele(a)]
    if bad:
        raise ValueError(f"malformed HLA allele(s), expected e.g. 'HLA-A*02:01': {bad}")


class HlaTyper(Strategy):
    """Seam: how the patient's class-I HLA genotype is determined - inferred from
    the normal reads, or taken from a published genotype when the sample is a
    characterized cell line."""
    @abstractmethod
    def type(self, case) -> list[str]:
        """Return the patient's MHC-I alleles, e.g. ['HLA-A*29:02', 'HLA-B*08:01', ...]."""

    def required_inputs(self, case) -> list:
        """Case files this typer needs (folded into the stage's declared inputs)."""
        return []

    def dry_check(self, case) -> None:
        """Cheap validation of this typer's inputs. Override if any."""
