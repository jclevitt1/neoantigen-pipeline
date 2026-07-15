# Output glossary — how to read the ranked table

Decoding `ranked.tsv` (stage 4 output), grounded in the **actual Option A run**.

## The real top-10 (the `pass` tier), from the run

| # | peptide | wt_peptide | gene | change | allele | binding_affinity (nM) | presentation | tier | agretopicity | dissim | immunogenicity |
|---|---------|-----------|------|--------|--------|----------------------:|-----------:|------|------------:|-------:|--------------:|
| 0 | GADGVGKSAL | GAGGVGKSAL | KRAS | G12D | C\*08:02 | 38.9 | 0.950 | pass | **22.57** | 1.0 | **3.116** |
| 1 | ARHGGWTTKM | AHHGGWTTKM | PIK3CA | H1047R | C\*07:01 | 44.0 | 0.839 | pass | 9.05 | 1.0 | 2.203 |
| 2 | KLVVVGAVGV | KLVVVGAGGV | KRAS | G12V | A\*02:01 | 52.3 | 0.716 | pass | 2.13 | 1.0 | 0.757 |
| 3 | VVGAVGVGK | VVGAGGVGK | KRAS | G12V | A\*11:01 | 42.8 | 0.912 | pass | 1.29 | 1.0 | 0.257 |
| 4 | VVVGAVGVGK | VVVGAGGVGK | KRAS | G12V | A\*11:01 | 35.8 | 0.959 | pass | 1.14 | 1.0 | 0.131 |
| 5 | ITDFGRAKLL | ITDFGLAKLL | EGFR | L858R | C\*08:02 | 95.0 | 0.732 | pass | 1.12 | 1.0 | 0.112 |
| 6 | KIGDFGLATEK | KIGDFGLATVK | BRAF | V600E | A\*11:01 | 52.9 | 0.857 | pass | 1.05 | 1.0 | 0.049 |
| 7 | ITDFGRAKL | ITDFGLAKL | EGFR | L858R | C\*08:02 | 35.6 | 0.933 | pass | 0.95 | 1.0 | −0.055 |
| 8 | VVVGADGVGK | VVVGAGGVGK | KRAS | G12D | A\*11:01 | 47.0 | 0.910 | pass | 0.87 | 1.0 | −0.139 |
| 9 | KITDFGRAK | KITDFGLAK | EGFR | L858R | A\*11:01 | 48.1 | 0.850 | pass | 0.58 | 1.0 | −0.547 |

Below row ~9, rows flip to `tier = low-presentation` and their recognition columns go
`NaN` (see "The three kinds of NaN" below).

## Column by column

- **`peptide`** — the candidate mutant peptide (an 8–11-mer window covering the
  mutation). This is what would go in the vaccine.
- **`wt_peptide`** — the *same window from the healthy (wild-type) protein*: what the
  peptide would be without the mutation. Row 0: `GADGVGKSAL` (mut) vs `GAGGVGKSAL`
  (wt) — differ only at the `D`/`G`. Carried so we can compare mutant-vs-WT binding.
- **`gene` / `transcript`** — which gene the mutation is in (`transcript` = the
  specific Ensembl isoform, MANE Select).
- **`protein_change`** — the mutation in standard notation
  **`[original AA][position][new AA]`**, amino acids as single letters. `G12D` =
  Glycine→Aspartate at residue 12. `H1047R` = His→Arg at 1047.
- **`length`** — peptide length (8–11; MHC-I mostly presents 8–11-mers).
- **`best_allele`** — of the patient's HLA genotype, the allele that presents this
  peptide best. The score is the *max* across the genotype (one patient, ≤6 alleles).
- **`binding_affinity`** (nM) — how tightly the peptide grips the MHC. **Lower =
  tighter.** ~38 nM (row 0) is strong; the gated-out rows show tens-of-thousands (weak).
- **`presentation_score`** (0–1) — MHCflurry's *eluted-ligand* score: probability the
  peptide is actually processed and displayed on the surface (not just that it binds).
  **The gate keeps `≥ 0.7`.** This is Axis 1.
- **`tier`** — the gate verdict: `pass` (cleared presentation + expression),
  `low-presentation` (< 0.7), `no-binding`, `no-expression`. Gated-out rows are
  *flagged and sunk, not deleted*.
- **`agretopicity`** — **the star, and the current ranking driver.** How much better
  the *mutant* binds than the *wild-type*. `>1` = the mutation made the peptide newly
  visible (great); `≈1` = no change (weak); `<1` = mutant binds worse (bad). Row 0's
  **22.6** = KRAS G12D binds C\*08:02 ~22× better than wild-type → the ideal
  "newly-revealed" neoantigen. See `concepts.md`.
- **`dissimilarity_to_self`** — how unlike your own normal proteins the peptide is
  (`1`=novel/good, `0`=self/tolerated). Currently the **MVP binary** version, so all
  pass rows read `1.0`. See `concepts.md`.
- **`immunogenicity`** — the final Łuksza quality score the table is **sorted by**.
  In this run it equals **`ln(agretopicity)`** exactly (row 0: `ln(22.57)=3.116` ✓),
  because the other two recognition terms are inert. This is why:
  - it **falls off a cliff**: `ln` collapses toward 0 as agretopicity → 1;
  - it goes **negative** (rows 7–9): agretopicity `<1` → `ln<0` → "mutation made the
    peptide *less* visible than the tolerated original" = actively bad target.
- **`tpm`** — gene **expression** (Transcripts Per Million). A mutation in a silent
  gene makes no protein → nothing to present. `NaN` here = unknown (Option A has no
  RNA); the gate runs permissive.
- **`vaf`** — variant allele fraction (what % of tumour DNA carries the mutation).
  Blank/`NaN` here — the curated variants claim no measured fraction.
- **Stage-5 eval columns** (in `filtered.tsv`): `autoimmunity_flag` (does it resemble
  self dangerously?), `clonality` (is the mutation in all tumour cells or a subclone?),
  `manufacturability` (can this peptide actually be synthesized cleanly?).

## Worked example — decode row 0 in one breath

> KRAS **G12D** peptide `GADGVGKSAL`, best presented on **HLA-C\*08:02** at binding
> 38.9 nM and presentation **0.95** (clears the gate → `pass`). Its **agretopicity is
> 22.6** — the mutant binds ~22× better than wild-type `GAGGVGKSAL`, i.e. the `G→D`
> change *created* this epitope. That drives the top **immunogenicity (3.12 = ln 22.6)**.
> And C\*08:02 is the *real* clinical restriction for KRAS G12D — the pipeline nailed it.

## The three kinds of NaN (all correct)

1. **`tpm` NaN everywhere** → no RNA/expression input in Option A (permissive gate).
2. **`vaf` NaN everywhere** → curated variants claim no allele fraction (honest blank).
3. **`immunogenicity` / `agretopicity` / `dissimilarity` NaN — only on
   `low-presentation` rows** → *by design*: recognition features are meaningless on
   peptides that won't be presented, so the ranker refuses to compute them and sinks
   the row with a tier tag. NaN in a `pass` row would be a bug; NaN in a gated row is
   the architecture. Yours are all the latter.

## A subtlety worth noticing

Rows 0 and 8 are *both* KRAS G12D — but different windows on different alleles: `#0`
on C\*08:02 has agretopicity 22.6 (great), `#8` on A\*11:01 has 0.87 (bad). **The same
mutation can be a brilliant neoantigen on one allele and a dud on another.** That's why
ranking is per-peptide-per-allele, and why HLA type matters so much.
