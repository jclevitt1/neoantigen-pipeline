# Approach: bwa (DNA) + STAR (RNA)

The planned normalization approach. `run()` branches on the input file type:

- **already BAM** → sort + index (passthrough)
- **CRAM** → decode against the reference → BAM
- **FASTQ, DNA** → `bwa mem` (contiguous alignment)
- **FASTQ, RNA** → `STAR` / `HISAT2` (**splice-aware** — the RNA-specific bit)

Every branch ends with: coordinate-sort + index (`.bai`) so downstream tools can
random-access by region.

## What's real now vs deferred

The **routing and header parsing are real and tested** (`plan.py`), tool-free:

- `normalization_plan(src, dst, modality)` — the branch table above, as an ordered
  list of `Step`s with concrete command templates. Enforces the DNA/RNA split
  (bwa vs STAR) and refuses FASTQ/CRAM without a reference.
- `parse_sam_header()` / `needs_sort()` — read `samtools view -H` output to skip a
  pointless re-sort when a BAM is already `SO:coordinate`.
- `contig_style()` — 'chr21' vs '21' check, so a reference/BAM naming mismatch is
  caught before it silently voids every coordinate lookup.

The tool **execution** (bwa/STAR/samtools) defers to Colab; `run()` assembles the
plan and raises with the exact commands rather than fabricating BAMs.

**Status:** planner + parser done & self-tested. For the MVP we operate on a small
pre-aligned subset (e.g. one chromosome of HCC1395), so the DNA path is just
`samtools sort` + `index`; RNA (FASTQ → STAR) lands with expression.

**Tools:** [bwa](https://github.com/lh3/bwa) · [STAR](https://github.com/alexdobin/STAR) · [samtools](https://www.htslib.org/) for sort/index.
