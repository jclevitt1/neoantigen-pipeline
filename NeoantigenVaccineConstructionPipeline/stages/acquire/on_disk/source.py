"""
OnDiskSource — the default acquire approach: the raw files are already staged.

Zero bytes fetched. Just verifies the three raw sample files are present (in your
local dir, a mounted Drive, or cloud scratch). If one is missing it raises,
telling you to either stage it or switch to a fetching source.
"""
from __future__ import annotations

from ..base import AcquireSource
from ... import checks


class OnDiskSource(AcquireSource):
    name = "on-disk"
    description = "Use raw sample files already present on disk / mounted storage (no download)."

    def ensure(self, case) -> None:
        missing = []
        for p in (case.tumor_dna, case.normal_dna, case.tumor_rna):
            try:
                checks.require_nonempty(p)
            except ValueError:
                missing.append(str(p))
        if missing:
            raise FileNotFoundError(
                "on-disk acquire: missing raw file(s):\n  " + "\n  ".join(missing)
                + "\nStage them there, or use a fetching source (e.g. Seqc2SliceSource)."
            )
