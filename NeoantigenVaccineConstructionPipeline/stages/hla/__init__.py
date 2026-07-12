"""
hla — stage 2b: type the patient's MHC-I alleles from the normal sample.

`HlaTypeStage` owns the contract; `HlaTyper` (base.py) is the pluggable approach.
Default `KnownGenotypeTyper` (published genotype, no reads). Switch to typing from
reads: `HlaTypeStage(case, typer=OptiTypeTyper())`.
"""
from .base import HlaTyper, is_valid_allele, validate_alleles
from .known.typer import KnownGenotypeTyper, KNOWN_GENOTYPES
from .optitype.typer import OptiTypeTyper, parse_optitype_tsv

# Default: published genotype lookup (zero inputs, runs today).
DEFAULT_TYPER = KnownGenotypeTyper

__all__ = [
    "HlaTyper", "is_valid_allele", "validate_alleles",
    "KnownGenotypeTyper", "KNOWN_GENOTYPES",
    "OptiTypeTyper", "parse_optitype_tsv",
    "DEFAULT_TYPER",
]
