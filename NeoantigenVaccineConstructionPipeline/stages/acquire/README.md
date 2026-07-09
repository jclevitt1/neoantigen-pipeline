# Stage 0 — Acquire

**Job:** make the Case's three raw sample files (`tumor_dna`, `normal_dna`,
`tumor_rna`) exist, then hand off to stage 1. Sits at the front of the DAG:

    0-acquire → 1-input → 2a/2b → 3 → 4 → 6 → 5

## Why it's a stage (and pluggable)

Getting the data is a real step with real trade-offs — most of all **where the
bytes live**. So it's a stage with two interchangeable `AcquireSource` approaches
(same pattern as `rank`'s pluggable `Ranker`):

- [`on_disk/`](on_disk/) — **default.** Files are already staged (local dir,
  mounted Drive, or cloud scratch). Verifies presence; fetches nothing.
- [`seqc2_slice/`](seqc2_slice/) — **region-slice** the remote SEQC2 aligned BAMs
  with `samtools view <url> <region>`. Pulls one chromosome (~hundreds of MB) not
  the whole genome (100s of GB). This is the cloud, disk-cheap path.

## The disk-space design (why this matters here)

Full HCC1395 WGS is 100s of GB — never needed. Neoantigens come from *coding*
mutations, and analysis is **region-local**: slicing to chr21 keeps *full depth*
on that chromosome (a complete, correct analysis of it) while touching a few GB.
Genome-scale = the same job run per-region and merged (scatter-gather), bounded by
whatever CPU/scratch you have — never the whole genome resident at once.

**Shared heavy assets** (reference genome + index, annotation cache, proteome) are
NOT acquired here — they're downloaded once by `cloud/` setup and reused across
every Case. This stage only handles per-case *sample* data.

## Bonus: SEQC2 ships ALIGNED BAMs

Because the source BAMs are already BWA-MEM aligned, the slice yields an aligned
BAM directly — so **stage 1 (normalize) is a light sort/index passthrough** for the
MVP and we skip alignment (bwa/STAR) entirely.

## I/O contract

| | |
|---|---|
| **Inputs** | none (external roots are remote / pre-staged) |
| **Outputs** | `tumor_dna`, `normal_dna`, `tumor_rna` (BAMs) |
| **Dry checks** | outputs non-empty + BGZF |
| **Caching** | empty inputs → "cached" iff outputs exist, so on-disk runs skip instantly |

## Data source

HCC1395 / HCC1395BL, SEQC2 project **SRA SRP162370** (public, no approval).
