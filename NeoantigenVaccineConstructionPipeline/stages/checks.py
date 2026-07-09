"""
checks.py — cheap "dry" validators shared across stages.

Each raises ValueError with context on failure, returns None on pass, so a
stage's dry_check_* method is just a few calls. None of these parse the whole
file — they sniff headers/magic bytes. Cheap enough to run every time.
"""
from __future__ import annotations

import json
from pathlib import Path


def require_nonempty(p) -> None:
    p = Path(p)
    if not p.exists() or p.stat().st_size == 0:
        raise ValueError(f"empty or missing: {p}")


def require_ext(p, exts: list[str]) -> None:
    joined = "".join(Path(p).suffixes).lower()  # 'x.fastq.gz' -> '.fastq.gz'
    if not any(joined.endswith(e) for e in exts):
        raise ValueError(f"{p} extension not in {exts}")


def require_bgzf(p) -> None:
    """BAM (and bgzipped) files start with the gzip/BGZF magic 1f 8b."""
    with open(p, "rb") as fh:
        magic = fh.read(2)
    if magic != b"\x1f\x8b":
        raise ValueError(f"{p} not gzip/BGZF (BAM?), magic={magic!r}")


def require_json(p) -> None:
    try:
        with open(p) as fh:
            json.load(fh)
    except Exception as e:  # noqa: BLE001 — surface any parse failure as one error
        raise ValueError(f"{p} not valid JSON: {e}")


def require_vcf(p) -> None:
    with open(p) as fh:
        first = fh.readline()
    if not first.startswith("##fileformat=VCF"):
        raise ValueError(f"{p} not a VCF (first line {first[:24]!r})")


def require_tsv_columns(p, cols: list[str]) -> None:
    with open(p) as fh:
        header = fh.readline().rstrip("\n").split("\t")
    missing = [c for c in cols if c not in header]
    if missing:
        raise ValueError(f"{p} missing columns {missing}; header={header}")


def require_fasta(p) -> None:
    with open(p) as fh:
        for line in fh:
            if line.strip():
                if not line.startswith(">"):
                    raise ValueError(f"{p} not FASTA (first line {line[:24]!r})")
                return
    raise ValueError(f"{p} empty FASTA")
