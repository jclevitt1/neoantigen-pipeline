"""
AcquireSource — the strategy plugged into stage 0 (acquire).

Like `Ranker` for stage 4, acquisition has interchangeable approaches: use files
already on disk, or fetch/slice them from a remote source. A source's one job is
to make the Case's three raw sample files exist. The Stage owns the contract.
"""
from __future__ import annotations

from abc import abstractmethod

from core import Strategy


class AcquireSource(Strategy):
    name: str = "unnamed-source"
    description: str = ""

    @abstractmethod
    def ensure(self, case) -> None:
        """Make case.tumor_dna / normal_dna / tumor_rna exist on disk (cloud
        scratch counts). Raise with a clear message if it cannot. Idempotent:
        if they already exist, do nothing."""
        raise NotImplementedError
