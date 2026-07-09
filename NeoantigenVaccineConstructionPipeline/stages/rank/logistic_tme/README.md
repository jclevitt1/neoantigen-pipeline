# Approach: Logistic TME (Model B) — FILLER

Wraps **Model B** from `../../../immunogenerative_logistic_abtest`. An L1-penalized
logistic regression over **31 peptide features + 22 TME-proxy features**.

## What it is / its one real claim

Peptide biochemistry alone doesn't generalize for immunogenicity (~0.6 AUC on
independent benchmarks — matches the whole field). Model B adds a **tumor
microenvironment (TME) proxy**: mean CIBERSORTx immune-cell fractions per cancer
type, from TCGA. Its defensible, statistically-tested claim:

> TME context adds a **significant** signal beyond peptide features —
> DeLong **p<0.001** on TESLA, bootstrap P(B≤A)≈0.001.

But absolute performance is **modest**: ROC-AUC ~**0.68** (TESLA), ~**0.57**
(HiTIDE). **Not clinical-grade.** Hence: filler. It holds the slot so the pipeline
runs end-to-end; the backlog item is to replace it (top-level `CLAUDE.md`).

## How `score()` works — fit once, score many

Training reads a 715 MB table and is slow, so we don't retrain per pipeline run:

1. A **fit step** (`fit_logistic_tme.py`, TODO) trains once and pickles a bundle:
   `{model, quantile_transformer, features, medians}` → `logistic_tme_model.pkl`.
2. `score()` loads the bundle, builds a feature matrix from the candidate rows
   (missing features → training median, mirroring Model B), and predicts.

Without the pickle, `score()` raises a clear "fit it first" error — it never
fabricates a number.

## Files
- `ranker.py` — `LogisticTmeRanker`
- `logistic_tme_model.pkl` — the pre-fit bundle (git-ignored; produced by the fit step)

## Reference
`../../../immunogenerative_logistic_abtest/RESULTS.md` — full Model A/B/C benchmarks,
TESLA/HiTIDE, DeLong statistics, feature list.
