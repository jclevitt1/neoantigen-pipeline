# Stage 1 — Input / Normalize

**Job:** take whatever raw sequencing files a data source gave us and turn them
into a uniform starting point: **three aligned BAMs** — tumor DNA, normal DNA,
tumor RNA.

## Why this stage exists

Public datasets ship in different formats: FASTQ(.gz) (raw reads, from SRA/dbGaP),
BAM (already aligned, from GDC/TCGA), or CRAM (compressed BAM). Everything
downstream assumes aligned BAMs. This stage absorbs that variability so no later
stage has to care where the data came from.

## The three samples (and why three)

- **tumor DNA** — the cancer's genome. Half of "the diff."
- **normal DNA** — the patient's healthy/germline genome (usually from blood). The
  control: it tells us the patient's *inherited* DNA so stage 2a can subtract it.
- **tumor RNA** — what the tumor is actually *transcribing*. Stage 3 uses it to
  drop mutations in genes that aren't expressed (no RNA → no protein → no target).

## Key concept: DNA vs RNA alignment differ

DNA aligns contiguously to the genome. RNA does **not** — introns are spliced out,
so a single RNA read can map across a gap of thousands of bases. RNA therefore
needs a **splice-aware** aligner (STAR/HISAT2), while DNA uses a straight aligner
(bwa). Getting this wrong silently corrupts expression numbers.

## I/O contract

| | |
|---|---|
| **Inputs** | `tumor_dna`, `normal_dna`, `tumor_rna` (external raw files) |
| **Outputs** | `tumor_dna.bam`, `normal_dna.bam`, `tumor_rna.bam` |
| **Dry checks** | inputs non-empty + known raw extension; outputs BGZF magic |

The routing (which tool per file kind + modality) and a `samtools view -H` header
parser are our own logic — real and self-tested in `align_bwa_star/plan.py`. Only
the tool run defers to Colab.

## Approaches

- [`align_bwa_star/`](align_bwa_star/) — bwa (DNA) + STAR (RNA) + samtools
  sort/index. Planner + header parser **done & tested**; tool execution deferred.
