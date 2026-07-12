"""
optitype/typer.py — real HLA typing from the normal DNA BAM via OptiType.

Split, exactly like stage 3's native/vcf.py: the OUTPUT PARSER is real and tested
now; only the tool EXECUTION defers to Colab (OptiType needs its razers3 mapper +
HLA reference). So `parse_optitype_tsv` is production code; `type()` is the stub.
"""
from __future__ import annotations

from ..base import HlaTyper

# OptiType's result TSV columns for the called genotype.
_ALLELE_COLS = ("A1", "A2", "B1", "B2", "C1", "C2")


def parse_optitype_tsv(text: str) -> list[str]:
    """Parse an OptiType result TSV into normalized 'HLA-A*02:01' alleles.

    OptiType writes a header row (an unnamed index column, then
    A1 A2 B1 B2 C1 C2 Reads Objective) and one result row with alleles like
    'A*02:01'. Homozygous genes repeat an allele; we collapse duplicates and
    keep A,B,C order. Empty cells (a gene that failed to type) are skipped.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        raise ValueError("OptiType TSV needs a header row and a result row")
    header = lines[0].split("\t")
    row = lines[1].split("\t")
    col = {h: i for i, h in enumerate(header)}
    present = [c for c in _ALLELE_COLS if c in col]
    if not present:
        raise ValueError(f"no A1/A2/B1/B2/C1/C2 columns in OptiType header: {header}")

    seen: set[str] = set()
    alleles: list[str] = []
    for c in present:
        raw = row[col[c]].strip() if col[c] < len(row) else ""
        if not raw or raw in (".", "NA"):
            continue
        allele = raw if raw.startswith("HLA-") else "HLA-" + raw
        if allele not in seen:
            seen.add(allele)
            alleles.append(allele)
    return alleles


class OptiTypeTyper(HlaTyper):
    """Type HLA-I from the normal BAM with OptiType (tool run deferred to Colab).

    Declares the normal DNA BAM as a required input, so wiring this in makes the
    `1-input → 2b-hla` DAG edge real. `type()` would run OptiType then hand its
    result TSV to `parse_optitype_tsv`.
    """

    def required_inputs(self, case) -> list:
        return [case.normal_dna_bam]

    def dry_check(self, case) -> None:
        from ... import checks
        checks.require_bgzf(case.normal_dna_bam)

    def type(self, case) -> list[str]:
        raise NotImplementedError(
            "OptiTypeTyper — run OptiType on the normal BAM, then parse_optitype_tsv (TODO, Colab)"
        )
