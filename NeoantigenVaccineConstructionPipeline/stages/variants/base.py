"""
base.py — the pluggable seam for stage 2a, plus the one piece of 2a we actually
*own* and can test today: the VEP-annotated-VCF **writer**.

Somatic calling has no free lunch — you cannot fake a tumor-minus-normal diff
without reads (unlike HLA, which has published germline genotypes, or expression,
which has an honest placeholder). So the DEFAULT source is a real tool adapter
(Mutect2 + VEP) whose execution defers to Colab.

What we can build and test now is the *contract* between 2a and stage 3: the exact
CSQ layout stage 3's native/vcf.py reads back. `write_annotated_vcf` is that writer.
A round-trip (write here -> parse in stage 3) is a hard, tool-free test that the
2a -> 3 hand-off is byte-compatible — see the stage's self_test.

    VariantSource (ABC)         produce(case, out_path) -> writes somatic.annotated.vcf
      ├─ Mutect2VepCaller       default; declares BAM+reference inputs; run defers to Colab
      └─ FixtureVariants        native; a labelled DIDACTIC variant; runs today, zero inputs
"""
from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path

from core import Strategy

# The CSQ subfields stage 3 (native/vcf.py) requires. Order here is the order we
# write; stage 3 reads the order from the header, so the two need only AGREE on
# the set — but keeping one canonical list in one place is what makes them agree.
CSQ_FIELDS = ["SYMBOL", "Feature", "Consequence", "Amino_acids",
              "Protein_position", "WildtypeProtein"]


@dataclass
class VariantRecord:
    """One protein-altering somatic variant, at the level of detail stage 3 needs.

    A single genomic locus can hit several transcripts; write_annotated_vcf groups
    records sharing (chrom, pos, ref, alt) into one VCF line with a comma-joined
    CSQ, exactly as VEP would — and exactly as stage 3 splits it back apart.
    """
    chrom: str
    pos: int
    ref: str          # reference DNA allele (nucleotides)
    alt: str          # tumor DNA allele
    gene: str         # CSQ SYMBOL
    transcript: str   # CSQ Feature
    ref_aa: str       # CSQ Amino_acids, left of '/'
    alt_aa: str       # CSQ Amino_acids, right of '/'
    protein_position: int          # 1-based, as VEP reports
    wildtype: str                  # WildtypeProtein (from VEP's protein plugin)
    consequence: str = "missense_variant"
    vaf: str = ""                  # tumor allele fraction -> FORMAT/AF


def _csq_value(rec: VariantRecord) -> str:
    """Serialize one record's CSQ subfields in CSQ_FIELDS order (pipe-delimited)."""
    by_name = {
        "SYMBOL": rec.gene,
        "Feature": rec.transcript,
        "Consequence": rec.consequence,
        "Amino_acids": f"{rec.ref_aa}/{rec.alt_aa}",
        "Protein_position": str(rec.protein_position),
        "WildtypeProtein": rec.wildtype,
    }
    return "|".join(by_name[name] for name in CSQ_FIELDS)


def write_annotated_vcf(records: list[VariantRecord], path) -> None:
    """Write records as a minimal, VEP-style annotated VCF at `path`.

    Records at the same locus are merged into one line with a comma-joined CSQ
    (multi-transcript), which is how VEP emits them and how stage 3 reads them.
    The header advertises the CSQ Format so stage 3 can locate subfields by name.
    """
    header = (
        "##fileformat=VCFv4.2\n"
        '##INFO=<ID=CSQ,Number=.,Type=String,Description="Consequence '
        "annotations from Ensembl VEP. Format: " + "|".join(CSQ_FIELDS) + '">\n'
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n'
        '##FORMAT=<ID=AF,Number=A,Type=Float,Description="Allele fraction">\n'
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tTUMOR\n"
    )

    # group by locus, preserving first-seen order
    order: list[tuple] = []
    grouped: dict[tuple, list[VariantRecord]] = {}
    for rec in records:
        key = (rec.chrom, rec.pos, rec.ref, rec.alt)
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(rec)

    lines = [header]
    for key in order:
        recs = grouped[key]
        chrom, pos, ref, alt = key
        csq = ",".join(_csq_value(r) for r in recs)
        vaf = next((r.vaf for r in recs if r.vaf), "")
        fmt, sample = ("GT:AF", f"0/1:{vaf}") if vaf else ("GT", "0/1")
        lines.append(
            f"{chrom}\t{pos}\t.\t{ref}\t{alt}\t.\tPASS\t"
            f"CSQ={csq}\t{fmt}\t{sample}\n"
        )

    Path(path).write_text("".join(lines))


class VariantSource(Strategy):
    """How stage 2a obtains the annotated somatic VCF. A pluggable seam like
    stage 4's Ranker / 2b's HlaTyper: each source declares its own inputs, so the
    DAG shows real edges only for the source in use."""

    @abstractmethod
    def produce(self, case, out_path) -> None:
        """Write the annotated somatic VCF to `out_path`."""

    def dry_check(self, case) -> None:
        """Cheap preflight on this source's inputs (default: nothing)."""
        return None
