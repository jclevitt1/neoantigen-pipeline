"""optitype — stage 2b approach: HLA-I typing from reads (OptiType)."""
from .typer import OptiTypeTyper, parse_optitype_tsv

__all__ = ["OptiTypeTyper", "parse_optitype_tsv"]
