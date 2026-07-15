# The concepts behind the ranker

The biology and method the stage-4 ranker encodes — enough to defend it in a
conversation. Deeper citations live in [`../ranking_methodology.md`](../ranking_methodology.md).

## 1. The two-axis model

Whether a mutated peptide triggers an anti-tumour T-cell response is really **two
questions in series**:

- **Axis 1 — Presentation:** will the peptide be physically displayed on the cell
  surface by an MHC-I molecule? Depends on binding + processing. **Well-solved**
  (~0.95 AUROC vs mass-spec). This is what MHCflurry does.
- **Axis 2 — Recognition:** *given* it's displayed, will a T cell actually see and
  react to it? Depends on the patient's T-cell repertoire and tolerance history.
  **Weak, half-solved** (~0.6 AUC field-wide — see §5).

Plus **modulators/gates**: expression (is the gene even on?) and clonality (is the
mutation in every tumour cell?).

## 2. Gate-then-rank — condition recognition on presentation

The design is **not** one blended model. It's: **gate on presentation first, then rank
the survivors on recognition.** Why: recognition features (agretopicity, foreignness)
are *meaningless on peptides that never get presented* — a peptide that isn't displayed
can't be recognized no matter how "foreign" it looks. So scoring recognition on
un-presented peptides just adds noise.

This is the lesson of the **TESLA consortium (Wells et al., Cell 2020)**: filtering on
presentation first is what made neoantigen prediction usable. In the code, gated-out
rows get a `tier` tag and their recognition columns are left blank (the `NaN`s you see)
rather than computed — deliberately.

## 3. The Łuksza recognition composite

For peptides that clear the gate, the recognition score is the **Łuksza fitness
quality**:

```
Q = R · ( log(A) + log(C) )
```

- **A = agretopicity (a.k.a. DAI, Differential Agretopicity Index)** = how much better
  the *mutant* binds MHC than the *wild-type*. High A = the mutation newly *reveals*
  the peptide (it wasn't presented before, so you're not tolerant to it).
- **C = dissimilarity-to-self** = how *unlike your own proteins* the peptide is.
- **R = foreignness** = how *like a known immunogenic (pathogen) epitope* it is.

### The C-vs-R contrast (they sound alike, they're opposite reference points)

| term | compares against | you want to be | biological reason |
|------|------------------|----------------|-------------------|
| **dissimilarity-to-self** (C) | your **own** proteins | **far** | so anti-self T cells weren't deleted in the thymus — the army *exists* |
| **foreignness** (R) | known **pathogen** epitopes (IEDB) | **near** | so a cross-reactive clone from past infections is *primed* — the army is *ready* |

One says *"not self."* The other says *"like known non-self."* Together they bracket
"will a T cell recognize it?" from both sides.

## 4. Why the current score reduces to `ln(agretopicity)`

In the Option A run, **two of the three recognition terms are inert**:
- **R (foreignness) is dormant** — no IEDB epitope set was supplied, so it returns a
  neutral `1` (multiplicative identity).
- **C (dissimilarity) is the MVP binary** — all pass rows are novel → `C=1` →
  `log(C)=0`.

So `Q = 1 · (log(A) + 0) = ln(agretopicity)`. That's why immunogenicity tracks the
agretopicity column exactly, why it cliffs (log collapses near 1), and why it goes
negative (agretopicity < 1). **To light up the full model you'd:** (a) pass a real
IEDB immunogenic set to activate R, and (b) upgrade C to the graded BLOSUM
nearest-self distance. Both are known next steps, not mysteries.

This idle-recognition state isn't a defect unique to this pipeline — it's the honest
state of the whole field (§5).

## 5. Field context (for cold-email credibility)

- **Presentation is solved; recognition isn't.** On honest benchmarks
  (negatives = presented-but-non-immunogenic peptides), *every* immunogenicity tool
  scores **AUC 0.52–0.60** (ITSNdb, Frontiers 2023). That's the real ceiling.
- **The flashy "~0.88 AUC" papers are leaking.** They build their negative set by
  *removing strong binders* (e.g. dropping IC50 ≤ 500 nM), so the model gets credit
  for separating binders from non-binders — the *solved* presentation axis — dressed
  up as immunogenicity. This is **selection leakage**: the benchmark fails to condition
  on presentation, and the inflation ≈ how much better presentation prediction is than
  recognition. Re-impose the condition and everyone drops back to ~0.6.
- **The TME finding (the abtest).** A logistic regression with a coarse
  cancer-type-level TME proxy adds a *statistically significant, controlled*
  improvement over peptide-only features on the independent TESLA benchmark
  (paired **DeLong p<0.001**; a cancer-type one-hot control, Model C, rules out "it's
  just cancer type"). This is a **feature claim** — "TME context carries immunogenicity
  signal the standard peptide×MHC models are structurally blind to" — *not* a
  leaderboard "beat SOTA" claim (the absolute AUCs are small-N-noisy and were never run
  head-to-head). The feature claim is the defensible, interesting one, and it points
  straight at TME-focused labs (Azizi, Han).
- **Why the data ceiling is structural.** Immunogenicity depends on the patient's
  *private, unobserved* T-cell repertoire (TCR side of a pMHC×TCR interaction). You're
  predicting an interaction from one side only — an information ceiling that more
  peptide data can't fix. That's why the moat is *labels + the TCR side*, mostly behind
  controlled-access clinical data.
