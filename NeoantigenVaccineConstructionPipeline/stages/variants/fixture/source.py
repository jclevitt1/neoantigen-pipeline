"""
source.py — FixtureVariants: a native stage-2a source that emits a small,
explicitly DIDACTIC set of annotated variants so the whole pipeline runs
end-to-end today with no tools and no reads.

READ THIS BEFORE TRUSTING THE OUTPUT: these are NOT a measurement. They are a
canonical textbook mutation on a real reference protein, used only to wire and
test the 2a -> 3 -> ... hand-off. HCC1395 does not carry KRAS G12D. The real
somatic calls come from Mutect2VepCaller in Colab. Nothing here is dressed up as
a patient's genotype — that would be fabricating scientific data.

Why it's still legitimate: the *shape* is exactly what VEP produces (SYMBOL,
Feature, Amino_acids, Protein_position, WildtypeProtein), and the WT sequence is
the genuine human KRAS N-terminus — so a peptide built from it is a real KRAS
peptide. Only the claim "this variant is present in the sample" is omitted, on
purpose, because for a fixture it isn't true.
"""
from __future__ import annotations

from ..base import VariantSource, VariantRecord, write_annotated_vcf

# Genuine human KRAS (UniProt P01116) N-terminal residues 1..20. Position 12 is
# the glycine of the G12D hotspot (…VVVGA[G]GVGK…). The rest of the CSQ mirrors a
# VEP call at chr12 GRCh38 for transcript ENST00000311936.
_KRAS_WT_1_20 = "MTEYKLVVVGAGGVGKSALT"

DEMO_VARIANTS = [
    VariantRecord(
        chrom="chr12", pos=25245350, ref="C", alt="T",
        gene="KRAS", transcript="ENST00000311936",
        ref_aa="G", alt_aa="D", protein_position=12,
        wildtype=_KRAS_WT_1_20,
        consequence="missense_variant", vaf="0.31",
    ),
]


class FixtureVariants(VariantSource):
    """Emit DEMO_VARIANTS as an annotated VCF. Zero inputs; runs today.

    Opt-in only: build the pipeline with `variant_source=FixtureVariants()` for a
    tool-free end-to-end wiring run. The default source is the real Mutect2+VEP
    adapter."""

    def __init__(self, records: list[VariantRecord] | None = None):
        self.records = records if records is not None else DEMO_VARIANTS

    def produce(self, case, out_path) -> None:
        write_annotated_vcf(self.records, out_path)
