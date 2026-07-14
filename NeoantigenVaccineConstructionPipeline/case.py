"""
Case — one patient's inputs + the derived paths every stage reads/writes.

Swapping HCC1395 -> COLO829 is one Case. Raw inputs may be BAM/CRAM/FASTQ
(source-dependent); Stage 1 normalizes them to the *_bam paths below. Everything
downstream is a fixed, typed filename under workdir, so stages reference
`case.ranked_tsv` etc. rather than juggling strings.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Case:
    sample_id: str
    workdir: Path              # all intermediates/outputs land here
    # --- raw inputs (external roots; type varies by source) ---
    tumor_dna: Path
    normal_dna: Path
    tumor_rna: Path
    # --- shared external references (roots) ---
    reference: Path            # genome FASTA (for alignment + variant calling)
    proteome: Path             # human proteome FASTA (stage 5 self-similarity)

    def __post_init__(self) -> None:
        self.workdir = Path(self.workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)

    def _p(self, name: str) -> Path:
        return self.workdir / name

    # --- stage 1 out: normalized BAMs ---
    @property
    def tumor_dna_bam(self) -> Path:  return self._p("tumor_dna.bam")
    @property
    def normal_dna_bam(self) -> Path: return self._p("normal_dna.bam")
    @property
    def tumor_rna_bam(self) -> Path:  return self._p("tumor_rna.bam")
    # --- stage 2a / 2b ---
    @property
    def somatic_vcf(self) -> Path:    return self._p("somatic.annotated.vcf")
    @property
    def hla_json(self) -> Path:       return self._p("hla.json")
    # --- stage 3 / 4 / 6 / 5 ---
    @property
    def candidates_tsv(self) -> Path: return self._p("candidates.tsv")
    @property
    def ranked_tsv(self) -> Path:     return self._p("ranked.tsv")
    @property
    def filtered_tsv(self) -> Path:   return self._p("filtered.tsv")
    @property
    def construct_fasta(self) -> Path: return self._p("construct.fasta")
    @property
    def construct_json(self) -> Path:  return self._p("construct.json")
