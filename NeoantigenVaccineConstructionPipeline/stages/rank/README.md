# Stage 4 — Rank

**Job:** score every candidate peptide for *this patient's* alleles — how well it
binds MHC, and how likely that presentation triggers a T-cell response — and sort
best-first. This is the differentiated core of the pipeline.

## Two sub-steps hiding in one stage

1. **Binding** — will the peptide be *displayed*? MHC binding is predicted by tools
   like **netMHCpan / MHCflurry**. This is where the allele-specific **anchor
   residue** preferences (position 2 + C-terminus) actually get applied — as a
   learned score, not a hand rule (see stage 3's README).
2. **Immunogenicity** — given it's displayed, will a T cell actually *react*? This
   is the harder, less-solved half, and the part our own model addresses.

The current ranker consumes binding ranks as input *features* and predicts
immunogenicity on top. So `binding_affinity` comes from the upstream tool;
`immunogenicity` is the model's output.

## Why this stage is pluggable (and others aren't)

Immunogenicity prediction is an open problem — no tool generalizes well (see the
filler's benchmarks). This is the one stage where we genuinely expect to swap
implementations, so scoring lives behind a `Ranker` interface (`base.py`) and each
approach is a subdir. Every other stage has one obvious tool; this one is a
bake-off. The Stage (`rank_stage.py`) only owns I/O and delegates.

## I/O contract

| | |
|---|---|
| **Inputs** | `candidates.tsv` (from stage 3), `hla.json` (from stage 2b — a skip-edge) |
| **Outputs** | `ranked.tsv` — candidates widened with `binding_affinity`, `immunogenicity`, sorted |
| **Dry checks** | input TSV has `peptide` + valid HLA JSON; output has the score columns |

## Approaches

- [`logistic_tme/`](logistic_tme/) — **default (filler)**. Model B: peptide + TME
  proxy logistic regression. Modest AUC; holds the slot.
- *(backlog)* a stronger predictor — see the top-level `CLAUDE.md` TODO. Requires a
  literature search on the best predictors of peptide immunoresponsiveness first.
