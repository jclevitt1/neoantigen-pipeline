# Approach: On-disk (default)

The raw sample files are already staged somewhere the process can read them — a
local directory, a mounted Google Drive, cloud-VM scratch, or a bucket path. This
source **fetches nothing**; it just verifies the three files are present and
non-empty, and raises a clear error naming any that are missing.

Because `AcquireStage` declares no inputs, the cache logic treats it as "done" the
moment the outputs exist — so with files already staged, stage 0 skips instantly.

**Use when:** you've already sliced/downloaded the data (e.g. a previous
`seqc2_slice` run persisted to Drive), or you're pointing at your own files.

`source.py` → `OnDiskSource`.
