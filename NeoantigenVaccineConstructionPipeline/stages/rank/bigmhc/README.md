# Approach: BigMHC_IM — OPTIONAL (non-commercial)

`BigMHcImRanker` wraps **BigMHC_IM** (Karchin lab, *Nat Mach Intell* 2023) — the
transfer-learning immunogenicity model with the highest reported precision on true
immunogenic neoepitopes (pretrained on mass-spec presentation, fine-tuned on
T-cell assay data).

## Why it's optional, not the default

- **Licence:** BigMHC Academic License — free for non-commercial use only. Do **not**
  ship it in a commercial build.
- **Install:** a ~5 GB `git clone` (weights included); **not** pip-installable.
- **Hardware:** GPU-friendly (Colab's free GPU works).

Contrast the default `mhcflurry` ranker, which is Apache-2.0, pip-installable, and
CPU-fine. So BigMHC sits behind the same `Ranker` seam as a swap-in for teams that
have cloned it and accept the terms.

## Status

Skeleton. Following the repo convention (cf. the logistic filler's missing pickle),
`score()` **never fabricates a number**: it raises a clear error if the BigMHC
checkout is absent, and a `NotImplementedError` marking the exact integration point
(shell out to BigMHC's `src/predict.py`, join the immunogenicity column back) if the
checkout is present but the adapter isn't wired.

## Wiring

```python
from NeoantigenVaccineConstructionPipeline.stages.rank.bigmhc import BigMHcImRanker
RankStage(case, ranker=BigMHcImRanker(bigmhc_dir="/path/to/bigmhc"))  # or $BIGMHC_DIR
```

## Reference

- BigMHC — https://github.com/KarchinLab/bigmhc ·
  https://www.nature.com/articles/s42256-023-00694-6
- `docs/ranking_methodology.md` §4 — why BigMHC_IM is the accuracy pick and
  DeepImmuno the commercial-safe one.
