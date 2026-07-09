# Stage 2a — Somatic Variant Calling ("the diff")

**Job:** find the mutations that are unique to the cancer — present in the tumor
DNA but not in the patient's normal DNA — and annotate what each one does to a
protein.

## The core idea: tumor minus normal

Both DNA samples are aligned to the same reference genome. At every position you
ask one question:

> Does the **tumor** show a DNA letter the **normal** doesn't?

The normal sample is the control — it captures the patient's *inherited* (germline)
DNA, quirks and all. Anything in the tumor but not the normal is **somatic**: the
cancer acquired it. That difference is "the diff." A caller does the statistics to
separate a real mutation from a sequencing error (is the alt letter in 40% of 30
reads, or 1 of 2?).

## Two steps folded into one stage

1. **Call** — produce a VCF of somatic positions + their ref→alt change.
2. **Annotate** — for each mutation, *which gene, and does it change an amino
   acid?* Most of the genome is non-coding or silent; those get dropped. The
   annotated VCF carries protein consequences (CSQ/ANN) so stage 3 can translate
   directly instead of re-deriving them.

## Units reminder

DNA letters are **nucleotides** (`A/C/G/T`). A triplet (codon) of nucleotides
encodes one **amino acid**. A mutation that changes an amino acid is what we care
about — it's the seed of a neoantigen.

## I/O contract

| | |
|---|---|
| **Inputs** | `tumor_dna.bam`, `normal_dna.bam`, `reference` (genome FASTA) |
| **Outputs** | `somatic.annotated.vcf` |
| **Dry checks** | inputs BGZF/non-empty; output is a `##fileformat=VCF` |

Also carries per-mutation **allele frequency** → later becomes the **CCF** that
stage 6 uses to judge clonal vs subclonal.

## Approaches

- [`mutect2_vep/`](mutect2_vep/) — Mutect2 for calling, VEP for annotation (planned).
