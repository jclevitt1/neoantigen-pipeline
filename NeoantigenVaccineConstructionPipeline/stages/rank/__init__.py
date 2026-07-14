"""
rank — stage 4: score candidate peptides for a patient's alleles.

`RankStage` (rank_stage.py) owns the file I/O and delegates scoring to a `Ranker`
(base.py). Rankers are interchangeable approaches, each in its own subdir.

Add a new ranker: subclass `Ranker`, implement `score()`, pass it to
`RankStage(case, ranker=...)`. Nothing else changes.
"""
from .base import Ranker
from .logistic_tme.ranker import LogisticTmeRanker
from .mhcflurry.ranker import LukszaCompositeRanker, MhcflurryPresentationRanker
from .bigmhc.ranker import BigMHcImRanker

# The default. LukszaCompositeRanker gates on MHCflurry presentation + expression,
# then ranks by the Luksza quality composite (agretopicity × dissimilarity-to-self)
# — see docs/ranking_methodology.md. Alternatives behind the same seam:
#   - MhcflurryPresentationRanker  Axis-1-only presentation ordering (simplest)
#   - LogisticTmeRanker            the original homegrown baseline (filler)
#   - BigMHcImRanker               optional non-commercial ML backend (BigMHC_IM)
DEFAULT_RANKER = LukszaCompositeRanker

__all__ = [
    "Ranker",
    "LukszaCompositeRanker",
    "MhcflurryPresentationRanker",
    "LogisticTmeRanker",
    "BigMHcImRanker",
    "DEFAULT_RANKER",
]
