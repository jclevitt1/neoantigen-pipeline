"""
mhcflurry — MHCflurry-backed stage-4 rankers (the modernized default).

  binding.py      MHCflurry 2.0 presentation/affinity wrapper (the one wet dep)
  recognition.py  pure Axis-2 math (agretopicity, dissimilarity, Luksza composite)
  ranker.py       MhcflurryPresentationRanker, LukszaCompositeRanker

See README.md and docs/ranking_methodology.md.
"""
from .ranker import LukszaCompositeRanker, MhcflurryPresentationRanker

__all__ = ["MhcflurryPresentationRanker", "LukszaCompositeRanker"]
