"""
known/typer.py — HLA genotype by lookup (no reads, no tool). The demo/benchmark path.

HLA type is germline, so for well-characterized cell lines it's already published;
we don't need to run a typer to get a *real* genotype for the demo Case. This is
the default typer: it makes stage 2b runnable today with zero inputs.
"""
from __future__ import annotations

from ..base import HlaTyper

# Published HLA class I genotypes for the benchmark tumor/normal pairs.
# Source: Cellosaurus (cellosaurus.org, CVCL_1249 / CVCL_1137), citing TCLP
# (Scholtalbers et al., "TCLP: an online cancer cell line catalogue integrating
# HLA type...", Genome Medicine 2015, PMID 26589293). HLA type is germline, so it
# is identical in the tumor line and its matched normal (…BL). Homozygous genes
# contribute a single allele (HCC1395 is HLA-A homozygous).
KNOWN_GENOTYPES = {
    "HCC1395": ["HLA-A*29:02", "HLA-B*08:01", "HLA-B*45:01", "HLA-C*06:02", "HLA-C*07:01"],
    "COLO829": ["HLA-A*01:01", "HLA-B*08:01", "HLA-B*40:02", "HLA-C*03:04", "HLA-C*07:06"],
}

# sample_id variants -> canonical table key (tumor line, its …BL normal, spacing)
_ALIASES = {
    "HCC1395BL": "HCC1395", "HCC1395_BL": "HCC1395",
    "COLO829BL": "COLO829", "COLO829_BL": "COLO829", "COLO 829": "COLO829",
}


class KnownGenotypeTyper(HlaTyper):
    """Look up a published HLA genotype by `case.sample_id`. Needs no inputs."""

    def __init__(self, table=None):
        self.table = table or KNOWN_GENOTYPES

    def type(self, case) -> list[str]:
        key = _ALIASES.get(case.sample_id, case.sample_id)
        if key not in self.table:
            raise KeyError(
                f"no known HLA genotype for sample_id={case.sample_id!r}; "
                f"known: {sorted(self.table)}. Use OptiTypeTyper to type from reads."
            )
        return list(self.table[key])
