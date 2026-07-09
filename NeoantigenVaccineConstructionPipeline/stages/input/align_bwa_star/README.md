# Approach: bwa (DNA) + STAR (RNA)

The planned normalization approach. `run()` branches on the input file type:

- **already BAM** → sort + index (passthrough)
- **CRAM** → decode against the reference → BAM
- **FASTQ, DNA** → `bwa mem` (contiguous alignment)
- **FASTQ, RNA** → `STAR` / `HISAT2` (**splice-aware** — the RNA-specific bit)

Every branch ends with: coordinate-sort + index (`.bai`) so downstream tools can
random-access by region.

**Status:** not implemented. For the MVP we operate on a small pre-aligned subset
(e.g. one chromosome of HCC1395), so this stage can stay a passthrough/stub.

**Tools:** [bwa](https://github.com/lh3/bwa) · [STAR](https://github.com/alexdobin/STAR) · [samtools](https://www.htslib.org/) for sort/index.
