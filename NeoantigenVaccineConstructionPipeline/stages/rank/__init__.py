"""
rank — stage 4: score candidate peptides for a patient's alleles.

`RankStage` (rank_stage.py) owns the file I/O and delegates scoring to a `Ranker`
(base.py). Rankers are interchangeable approaches, each in its own subdir.

Add a new ranker: subclass `Ranker`, implement `score()`, pass it to
`RankStage(case, ranker=...)`. Nothing else changes.
"""
from .base import Ranker
from .logistic_tme.ranker import LogisticTmeRanker

# The default until something stronger lands. LogisticTmeRanker is a documented
# filler (modest AUC), not a final choice — see logistic_tme/README.md.
DEFAULT_RANKER = LogisticTmeRanker

__all__ = ["Ranker", "LogisticTmeRanker", "DEFAULT_RANKER"]
