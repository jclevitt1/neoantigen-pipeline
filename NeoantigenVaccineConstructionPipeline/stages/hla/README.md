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
| **Inputs** | `normal_dna.bam` |
| **Outputs** | `hla.json` — tiny; the ~6 alleles, e.g. `{"alleles": ["HLA-A*02:01", ...]}` |
| **Dry checks** | input BGZF; output valid JSON (TODO: standard HLA nomenclature) |

## Approaches

- [`optitype/`](optitype/) — OptiType HLA-I typing from sequencing reads (planned).
