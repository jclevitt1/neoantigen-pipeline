# Stage 2b — HLA Typing

**Job:** read out the patient's own **MHC-I alleles** (the ~6 classical ones) from
the normal sample, so stage 4 knows which molecules will present the peptides.

## Why this is mandatory, not optional

Binding is **allele-specific**. An MHC-I molecule is a groove that grips some
peptides and not others, and *which* peptides depends entirely on the exact allele.
Every human carries a personal set of these alleles. Predict binding against the
wrong alleles and every downstream score is meaningless. This stage is what makes
the vaccine *personalized* at the presentation level.

## What an "allele" is here

Humans have three classical MHC-I genes — **HLA-A, HLA-B, HLA-C** — and you inherit
two copies of each (one per parent), so ~**6 alleles** total. Each allele has a
standardized name like `HLA-A*02:01`. Some people are homozygous at a gene, giving
fewer than 6 distinct alleles.

## Read from the *normal* sample — why

HLA type is inherited (germline), so you read it from normal DNA, not tumor.
(Tumors can even *lose* an HLA allele — "LOH" — but the patient's baseline type
comes from normal.)

## I/O contract

| | |
|---|---|
| **Inputs** | `normal_dna.bam` *(only when a read-based typer is used; the default `known` typer needs none)* |
| **Outputs** | `hla.json` — tiny; `{"sample_id":…, "alleles": ["HLA-A*02:01", …], "source":…}` |
| **Dry checks** | input BGZF (read-based typer); output valid JSON + every allele in class-I nomenclature (`HLA-[ABC]*NN:NN`) |

The typer is a **pluggable seam** (`base.py`, like stage 4's `Ranker`): it declares
its own required inputs, so with the default `known` typer stage 2b has zero inputs
and runs today; swap in `optitype` and the normal BAM becomes a real DAG input.

## Approaches

- [`known/`](known/) — **default**: published HLA genotype by `sample_id` (HCC1395,
  COLO829), sourced from Cellosaurus/TCLP. No reads, no tool — runs today.
- [`optitype/`](optitype/) — OptiType HLA-I typing from sequencing reads. Output
  **parser is real and tested now**; the tool run defers to Colab.
