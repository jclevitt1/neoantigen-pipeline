"""
acquire — stage 0: make the raw sample files exist.

`AcquireStage` owns the contract; `AcquireSource` (base.py) is the pluggable
approach. Default is on-disk (no download). Switch to a fetching source by
passing it: `AcquireStage(case, source=Seqc2SliceSource(manifest, region))`.
"""
from .base import AcquireSource
from .on_disk.source import OnDiskSource
from .seqc2_slice.source import Seqc2SliceSource, seqc2_wes_dna_manifest

# Default: assume files are already staged (zero bytes fetched).
DEFAULT_SOURCE = OnDiskSource

__all__ = [
    "AcquireSource", "OnDiskSource", "Seqc2SliceSource",
    "seqc2_wes_dna_manifest", "DEFAULT_SOURCE",
]
