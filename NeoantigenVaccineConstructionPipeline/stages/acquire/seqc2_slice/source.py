"""
Seqc2SliceSource — fetch a genomic REGION from remote SEQC2 BAMs, no full download.

SEQC2 (SRA project SRP162370) published BWA-MEM–aligned, INDEXED BAMs for the
HCC1395 / HCC1395BL tumor-normal pair. Because they're aligned and indexed, we can
pull just one region with `samtools view <remote-url> <region>` — the reads for,
say, chr21 (a few hundred MB) instead of the whole genome (100s of GB). This is
the cloud, disk-cheap acquire path.

VERIFIED locations (browsed 2026-07; both .bam and co-located .bai present):
  WES DNA base: https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/seqc/Somatic_Mutation_WG/data/WES
  pattern:      WES_<CENTER>_<T|N>_<rep>.bwa.dedup.bam   e.g. WES_EA_T_1.bwa.dedup.bam
  -> use `seqc2_wes_dna_manifest()` below to build the DNA manifest.

NOT here: tumor RNA. SEQC2 RNA-seq is raw FASTQ under SRA SRX8401273-5
(BioProject PRJNA635123) — needs a STAR alignment first, so it's a separate
follow-up, not a same-pattern slice. Run DNA-only for now (partial manifest OK);
expression tagging (stage 3) is a starter until the RNA BAM exists.

Remote-slice requirements: the host supports HTTP range requests (NCBI FTP does)
AND the .bai is co-located (it is). Contig naming (chr21 vs 21) — confirm once with
`samtools view -H <url> | grep '@SQ' | head` and set `region` to match.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..base import AcquireSource

DEFAULT_REGION = "chr21"  # smallest gene-bearing autosome — cheap, real; confirm 'chr' prefix
_SAMPLES = ("tumor_dna", "normal_dna", "tumor_rna")

# Verified SEQC2 WES DNA location + filename pattern (see module docstring).
WES_BASE = "https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/seqc/Somatic_Mutation_WG/data/WES"


def seqc2_wes_dna_manifest(center: str = "EA", tumor_rep: int = 1,
                           normal_rep: int = 1) -> dict[str, str]:
    """Build the tumor+normal DNA manifest from the verified WES pattern. Any
    center (EA/FD/IL/LL/NC/NV) with a matched T/N pair works; EA_T_1 / EA_N_1 is
    the default demo pair. (RNA is intentionally absent — see module docstring.)"""
    return {
        "tumor_dna":  f"{WES_BASE}/WES_{center}_T_{tumor_rep}.bwa.dedup.bam",
        "normal_dna": f"{WES_BASE}/WES_{center}_N_{normal_rep}.bwa.dedup.bam",
    }


class Seqc2SliceSource(AcquireSource):
    name = "seqc2-slice"
    description = "Region-slice remote SEQC2 aligned BAMs (samtools view <url> <region>); no full download."

    def __init__(self, manifest: dict[str, str], region: str = DEFAULT_REGION):
        bad = [s for s in manifest if s not in _SAMPLES]
        if bad:
            raise ValueError(f"manifest has unknown sample keys {bad}; valid: {list(_SAMPLES)}")
        if not manifest:
            raise ValueError("empty manifest — provide at least one sample URL")
        self.manifest = manifest  # partial OK (e.g. DNA-only)
        self.region = region

    def _samtools(self, *args) -> None:
        if shutil.which("samtools") is None:
            raise RuntimeError(
                "samtools not found on PATH. Install it first "
                "(Colab: `!apt-get -qq install -y samtools`)."
            )
        subprocess.run(["samtools", *args], check=True)

    def ensure(self, case) -> None:
        for sample, url in self.manifest.items():
            out = Path(getattr(case, sample))
            if out.exists() and out.stat().st_size > 0:
                continue  # idempotent — already sliced
            out.parent.mkdir(parents=True, exist_ok=True)
            # -b BAM out, -h keep header (needed for a valid standalone BAM)
            self._samtools("view", "-b", "-h", url, self.region, "-o", str(out))
            self._samtools("index", str(out))
