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
| **Inputs** | `tumor_dna.bam`, `normal_dna.bam`, `reference` (genome FASTA) — *declared by the source in use; the fixture source needs none* |
| **Outputs** | `somatic.annotated.vcf` (VEP-style CSQ with `WildtypeProtein`) |
| **Dry checks** | inputs BGZF/non-empty (real source); output is a `##fileformat=VCF` **advertising a CSQ header** |

Also carries per-mutation **allele frequency** (FORMAT/AF) → later becomes the
**CCF** that stage 6 uses to judge clonal vs subclonal.

The caller+annotator is a **pluggable seam** (`base.py`, like stage 4's `Ranker`
and 2b's `HlaTyper`): each source declares its own inputs. The one piece 2a *owns*
and tests today is `write_annotated_vcf` — the writer that emits exactly the CSQ
layout stage 3 reads. `self_test` round-trips it **through stage 3's own parser**,
so the 2a→3 hand-off is proven byte-compatible with zero tools.

Unlike 2b (published germline genotypes) and stage 3's expression (honest
placeholder), somatic calling **can't be faked from nothing** — so the *default*
source is the real tool adapter, deferred to Colab. A fixture source exists only
to wire/test the rest of the pipeline.

## Approaches

- [`mutect2_vep/`](mutect2_vep/) — **default**: Mutect2 (call) + VEP (annotate,
  `--plugin Wildtype`). Declares the BAM+reference inputs; execution defers to
  Colab (see its `COMMAND_PLAN`). The honest scientific path.
- [`fixture/`](fixture/) — **opt-in, native**: a labelled *didactic* variant
  (KRAS G12D on the real KRAS protein — **not** a sample measurement). Zero
  inputs, runs today, for a tool-free end-to-end run. Pass
  `variant_source=FixtureVariants()`.
