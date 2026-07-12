# Stage 3 — Candidate Generation

**Job:** turn each protein-changing mutation into the short peptides that could
actually be shown to the immune system, and tag each with how strongly its gene is
expressed.

## The sliding window

A mutation swaps one amino acid in a protein. That single change creates short
stretches the immune system has **never seen** — they exist in no normal human
protein. To enumerate them, slide an **8–11 amino-acid** window across the mutated
position:

```
normal protein:   ... L Q A [G] R T V ...
mutant protein:   ... L Q A [E] R T V ...     ← one letter changed
candidate 9mers containing E:  LQAERTV.. , QAERTV.. , AERTV.. , ...
```

**Why 8–11:** that's the length MHC-I physically holds (9 is most common). Each
window that *contains the mutation* is a neoantigen candidate.

## Why we don't hand-filter the window (anchor residues)

You might expect a rule like "position 2 must be L/M." That preference is real
(**anchor residues** at position 2 and the C-terminus), but it's **allele-specific
and soft**, so we don't prefilter on it. Instead every window is generated here and
the **binding predictor in stage 4** — which has learned anchor preferences per
allele — narrows them by *score*. Narrowing by scoring beats a brittle letter rule.

## Expression tagging

Each candidate is tagged with **TPM** (transcripts per million) from the tumor RNA
BAM. If the gene isn't transcribed, there's no protein and no target — drop it.
Silent-but-present mutations die here. (Complementary metric: mutant-allele
fraction in RNA — how often the mutated copy is the one transcribed.)

## I/O contract

| | |
|---|---|
| **Inputs** | `somatic.annotated.vcf`, `tumor_rna.bam` |
| **Outputs** | `candidates.tsv` — at minimum `peptide`, `tpm` (later stages add columns) |
| **Dry checks** | input VCF + BGZF RNA; output TSV has `peptide`,`tpm` |

The `candidates.tsv` is the table that travels 3 → 4 → 6, gaining columns at each
stage.

## Approaches

- [`native/`](native/) — **our own** window generator (default). Pure sliding-window
  logic + a minimal VEP-annotated-VCF reader + a pluggable expression tag. No
  external tool; hard-tested from `self_test` on a fixture VCF. Handles missense;
  frameshift/indel is a documented extension.
- [`pvacseq/`](pvacseq/) — pVACseq for window generation + expression join
  (production-scale alternative, planned).
