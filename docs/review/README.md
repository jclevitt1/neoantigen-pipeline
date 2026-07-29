# Pre-cold-email review pack

_A self-contained walk-through of what this pipeline does, what was built and
validated, and how to read its output — so you can review it cold before writing to
labs, and answer "what did you actually do?" without re-deriving it._

Read in this order:
1. **This file** — what was accomplished + the honest state.
2. [`output_glossary.md`](output_glossary.md) — every column of the ranked output, decoded on the real run.
3. [`concepts.md`](concepts.md) — the biology/method behind the ranker (two-axis model, gate-then-rank, the Łuksza composite, the field's honest limits).

---

## What this pipeline is

An **in-silico neoantigen cancer-vaccine DESIGN pipeline**: given a tumour's
mutations + the patient's HLA type, it decides *which mutated peptides to put in a
personalized vaccine*. It stops where silicon hands off to wet lab. Staged DAG
(0 acquire → 1 input → 2a variants → 2b HLA → 3 candidates → 4 rank → 5 eval →
6 construct); each stage is a pluggable, self-tested block.

## What was accomplished (the honest list)

- **Modernized the ranking (stage 4) to a two-axis, gate-then-rank design.** Replaced
  a homegrown logistic-regression filler with: an **MHCflurry 2.0 presentation gate**
  (Axis 1 — "will it be displayed on MHC?") followed by a **Łuksza recognition
  composite** (Axis 2 — "will a T cell react?"). Rationale + citations in
  [`../ranking_methodology.md`](../ranking_methodology.md). Committed.

- **Ran the ranking back half (stages 3→6) end-to-end on real mutations** (Option A
  component test, in Colab). Fed a curated panel of real oncogenic hotspots
  (KRAS G12D/G12V, BRAF V600E, TP53 R175H, PIK3CA H1047R, EGFR L858R) through
  windows → presentation gate → composite → vaccine construct. **It ran clean, and the
  built-in positive control passed:**
  - **#1 hit: KRAS G12D on HLA-C\*08:02** — the *real, clinically-validated*
    restriction (Tran/Rosenberg, NEJM 2016, where TILs against exactly this
    neoantigen drove regression of all seven lung metastases).
  - **This is a positive control, not a discovery.** `DEMO_HLA_PANEL`
    ([`curated.py`](../../NeoantigenVaccineConstructionPipeline/stages/variants/fixture/curated.py))
    was *deliberately built* to contain the published restricting alleles for these
    hotspots, and the ranker picks the best allele from the genotype it is given. What
    the run demonstrates is that, given a 6-allele genotype and 6 hotspot mutations,
    MHCflurry recovered the correct peptide–allele pairing and the composite ranked it
    first — the control behaved as designed. It does **not** show the pipeline finding
    a restriction nobody told it about.
  - **#2: PIK3CA H1047R** (the single most common PIK3CA driver mutation).
  - KRAS G12V likewise recovered on **HLA-A\*11:01** (also its real restriction, also
    seeded into the panel).
  - See the captured table in [`output_glossary.md`](output_glossary.md).

- **A separate statistical result (the "abtest"):** a logistic regression showed that
  a **tumour-microenvironment (TME) proxy adds statistically significant signal**
  beyond peptide biochemistry for immunogenicity — paired DeLong **p < 0.001**, with
  bootstrap 95% CIs. Scoped honestly (see "what NOT to claim" below).

- **Documentation:** methodology doc, E2E validation plan
  ([`../e2e_validation_notes.md`](../e2e_validation_notes.md)), and this review pack.

## The honest state — what's real vs. scaffolded

- **Presentation (Axis 1) is real and strong.** MHCflurry is a validated, published
  model (~0.95 AUROC vs mass-spec). The gate works.
- **Recognition (Axis 2) is scaffolded but partly idle.** In the Option A run:
  - **Agretopicity** (mutant-vs-WT binding) is live and doing the ranking.
  - **Dissimilarity-to-self** is an MVP *binary* proxy (novel=1 / exact-self=0); the
    graded version is a TODO.
  - **Foreignness** is *dormant* (no IEDB epitope set supplied → returns neutral 1).
  - Net effect: the score currently reduces to **`ln(agretopicity)`** (see
    [`concepts.md`](concepts.md)). This mirrors the field: recognition is the weak,
    half-solved axis everywhere, not just here.
- **Expression** ran permissive in Option A (no RNA data → unknown TPM survives).
- **Option B** (HCC1395, from the published SEQC2 somatic truth VCF, chr21) **was run**
  on 2026-07-17 — results and caveats in [`option_B_result.md`](option_B_result.md).
  **Caveat on the evidence:** it ran out-of-tree in an ephemeral sandbox, and **no
  artifacts were committed** — no notebook outputs, no `ranked.tsv`/`construct.fasta`,
  no command log — and the exact procedure used (VEP in GFF+FASTA mode, a byte-range
  chr21 reference extract, `gffread` splicing the WT protein back into the CSQ) is not
  in the repo. Treat it as a reported result that is **not currently reproducible**,
  including by me. Reproducing it is tracked work.
- **Only one stage lacks a self-test:** `0-acquire`. The other seven carry hard fixture
  assertions. Note that stage 4's self-test covers the recognition math only — the
  MHCflurry presentation calls are exercised in Colab, not by the test.

## For the cold emails — claims you CAN defend, and what NOT to say

**Defensible:**
- "Built a modular, tested neoantigen-design pipeline and ran it end-to-end on real
  mutations. My positive control — a curated hotspot panel with the published
  restricting alleles in the genotype — comes back correct: KRAS G12D pairs to
  C\*08:02 and ranks first."
- "A coarse TME proxy adds *statistically significant* orthogonal signal for
  immunogenicity (paired DeLong p<0.001)."
- "I benchmarked on the *hard* task — presented-but-non-immunogenic negatives — where
  the field sits ~0.6, not the leaky ~0.88 benchmarks."

**Do NOT claim:** that the pipeline *discovered* the KRAS G12D → C\*08:02 restriction.
The allele panel was seeded with it; recovering it is a passing control, and calling it
anything more is the first thing a reviewer will catch when they open `curated.py`.

**Do NOT claim:** "beat SOTA." The absolute AUCs are small-N-noisy and were never run
head-to-head against other models on one fixed split. The *feature* finding (TME adds
signal) is the real, scoped result — not a leaderboard win. Detail in `concepts.md`.
