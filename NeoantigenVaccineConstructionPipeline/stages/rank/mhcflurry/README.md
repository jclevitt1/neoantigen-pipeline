# Approach: MHCflurry composite — DEFAULT

The modernized stage-4 ranker. Implements the two-axis, gate-then-rank design from
[`docs/ranking_methodology.md`](../../../../docs/ranking_methodology.md).

## Two rankers, one seam

- **`LukszaCompositeRanker`** (the default) —
  1. **Presentation gate (Axis 1).** Score each peptide × the patient's alleles with
     **MHCflurry 2.0**'s eluted-ligand presentation model. Keep as `pass` only those
     that clear `PRESENT_MIN` (0.7) *and* are expressed (a real `tpm` > 0; unknown
     survives). Everything else gets a `tier` label (`low-presentation`,
     `no-expression`, `no-binding`) and sinks — flagged, not dropped.
  2. **Recognition composite (Axis 2), on survivors.** Rank by the Łuksza quality
     `Q = R · D`, `D = log(A) + log(C)`:
     - **A = agretopicity (DAI)** = `Kd_WT / Kd_MT` — the mutant's affinity vs its
       wild-type counterpart (stage 3 now emits `wt_peptide`; we score it at the
       mutant's best allele so we compare like with like).
     - **C = dissimilarity-to-self** — MVP binary proxy vs the proteome (0 = verbatim
       self, 1 = novel). True nearest-neighbour BLOSUM distance is the TODO.
     - **R = foreignness** — dormant by default (returns neutral 1.0); supply an IEDB
       immunogenic set to `LukszaCompositeRanker(iedb_epitopes=...)` to enable
       Łuksza's TCR cross-reactivity term.

- **`MhcflurryPresentationRanker`** — Axis 1 only: order purely by presentation
  score. The smallest possible drop-in replacement for the logistic filler, and a
  useful sanity baseline.

## Why MHCflurry 2.0

Free, **Apache-2.0 (redistributable)**, `pip install mhcflurry`, runs fully offline
in Colab, and outputs a real **presentation** score (not just an IC50). See the
methodology doc §3 for the comparison vs NetMHCpan (non-redistributable) and BigMHC.

## Files

- `binding.py` — the one wet dependency. MHCflurry is imported **lazily** (inside
  methods) so the rest of stage 4 imports and self-tests without the package.
- `recognition.py` — pure Axis-2 math (agretopicity, dissimilarity, foreignness,
  the Łuksza composite). No I/O, no MHCflurry — unit-tested from the stage's
  `self_test`.
- `ranker.py` — the two `Ranker` implementations above.

## Setup (Colab)

```
!pip install mhcflurry
!mhcflurry-downloads fetch models_class1_presentation
```

Then the default pipeline just works — `RankStage` uses `LukszaCompositeRanker`
out of the box.

## Reference

`docs/ranking_methodology.md` — the SOTA sweep, the condition-on-presentation
rationale (TESLA / Wells 2020), the Łuksza fitness model, and why each model was
chosen or set aside.
