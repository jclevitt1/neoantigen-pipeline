"""
plan.py — the owned, tool-free heart of stage 1: decide *what* normalization a
raw file needs, and read a BAM header to check what's already been done.

The tools (bwa/STAR/samtools) run in Colab, but the *routing* — "this is an
aligned BAM, so just sort+index; that's RNA FASTQ, so splice-align with STAR" —
is our logic and is fully testable here on fixtures, exactly like stage 3's VCF
parser or stage 2b's OptiType parser.

Two pieces:
  1. normalization_plan(src, dst, modality) -> ordered [Step]  (the branch table)
  2. parse_sam_header(text)                 -> {sort_order, contigs}  (a real parser
     over `samtools view -H` output, used to skip a needless re-sort and to catch
     the classic chr21-vs-21 contig-naming mismatch before it corrupts a run)
"""
from __future__ import annotations

from dataclasses import dataclass

# raw extensions we know how to normalize (longest suffixes first so .fastq.gz
# is matched before .gz would be)
_FASTQ_EXTS = (".fastq.gz", ".fq.gz", ".fastq", ".fq")


@dataclass
class Step:
    """One tool invocation in a normalization plan. `command` is a template a
    Colab cell fills in and runs — kept beside the routing so intent and
    invocation can't drift."""
    tool: str       # samtools | bwa | STAR
    action: str     # sort | index | decode | align
    command: str


def classify(path) -> str:
    """Coarse kind of a raw sequencing file: 'bam' | 'cram' | 'fastq'.

    Raises ValueError on an unrecognized extension — better a loud stop than a
    silent mis-route that produces a corrupt BAM three tools later.
    """
    name = str(path).lower()
    if name.endswith(".bam"):
        return "bam"
    if name.endswith(".cram"):
        return "cram"
    if any(name.endswith(e) for e in _FASTQ_EXTS):
        return "fastq"
    raise ValueError(f"unrecognized raw sequencing file (not BAM/CRAM/FASTQ): {path}")


def normalization_plan(src, dst, modality: str, reference=None) -> list[Step]:
    """Ordered steps to turn raw `src` into a coordinate-sorted, indexed BAM `dst`.

    modality: 'dna' -> bwa (contiguous)  |  'rna' -> STAR (splice-aware). Getting
    this wrong silently corrupts expression, so it's an explicit argument, never
    guessed. `reference` is required to decode CRAM or to align FASTQ; an aligned
    BAM needs none (the SEQC2 MVP path -> just sort + index).
    """
    if modality not in ("dna", "rna"):
        raise ValueError(f"modality must be 'dna' or 'rna', got {modality!r}")
    kind = classify(src)
    steps: list[Step] = []
    tmp = f"{dst}.unsorted"

    if kind == "bam":
        steps.append(Step("samtools", "sort", f"samtools sort -o {dst} {src}"))
    elif kind == "cram":
        if reference is None:
            raise ValueError("CRAM decode needs a reference FASTA")
        steps.append(Step("samtools", "decode",
                          f"samtools view -b -T {reference} -o {tmp} {src}"))
        steps.append(Step("samtools", "sort", f"samtools sort -o {dst} {tmp}"))
    else:  # fastq
        if reference is None:
            raise ValueError("aligning FASTQ needs a reference/genome index")
        if modality == "rna":
            steps.append(Step("STAR", "align",
                              f"STAR --genomeDir {reference} --readFilesIn {src} "
                              f"--outSAMtype BAM Unsorted --outFileNamePrefix {tmp}."))
        else:
            steps.append(Step("bwa", "align",
                              f"bwa mem {reference} {src} | samtools view -b -o {tmp} -"))
        steps.append(Step("samtools", "sort", f"samtools sort -o {dst} {tmp}"))

    # every path ends coordinate-sorted + indexed so downstream tools random-access by region
    steps.append(Step("samtools", "index", f"samtools index {dst}"))
    return steps


def parse_sam_header(text: str) -> dict:
    """Parse `samtools view -H` output (SAM header lines) into what stage 1 cares
    about: the sort order (@HD SO:) and the contig names (@SQ SN:)."""
    sort_order = "unknown"
    contigs: list[str] = []
    for line in text.splitlines():
        if line.startswith("@HD"):
            for tag in line.split("\t")[1:]:
                if tag.startswith("SO:"):
                    sort_order = tag[3:]
        elif line.startswith("@SQ"):
            for tag in line.split("\t")[1:]:
                if tag.startswith("SN:"):
                    contigs.append(tag[3:])
    return {"sort_order": sort_order, "contigs": contigs}


def needs_sort(header_text: str) -> bool:
    """True unless the header already says SO:coordinate — lets a pre-sorted BAM
    skip a pointless (and slow) re-sort."""
    return parse_sam_header(header_text)["sort_order"] != "coordinate"


def contig_style(contigs) -> str:
    """'chr' (chr21), 'plain' (21), 'mixed', or 'unknown' (empty). The reference
    and the BAM must agree, or every coordinate lookup silently misses — the
    chr21-vs-21 gotcha called out in the data notes."""
    if not contigs:
        return "unknown"
    chr_prefixed = [c.startswith("chr") for c in contigs]
    if all(chr_prefixed):
        return "chr"
    if not any(chr_prefixed):
        return "plain"
    return "mixed"
