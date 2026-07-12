"""
Stage 1 — Input / Normalize.  (adapter; contract + orchestration)

Maps whatever the public source gave us -> three normalized (coordinate-sorted,
indexed) BAMs: tumor DNA, normal DNA, tumor RNA. The *routing* (which tool per
file kind/modality) is our own logic and lives in the approach's plan.py, hard-
tested here; the tool *execution* (bwa/STAR/samtools) defers to Colab. See
stages/input/README.md and align_bwa_star/README.md.

Modality matters: tumor RNA is splice-aligned (STAR), the two DNA samples are
aligned contiguously (bwa). For the SEQC2 MVP the DNA inputs arrive already
aligned, so their plan is just sort + index.
"""
from __future__ import annotations

from core import Stage
from .. import checks
from .align_bwa_star import normalization_plan

_RAW_EXTS = [".bam", ".cram", ".fastq", ".fq", ".fastq.gz", ".fq.gz", ".sra"]


class InputStage(Stage):
    name = "1-input"
    kind = "adapter"
    description = "Normalize raw sequencing (FASTQ/BAM/CRAM) into three aligned BAMs."

    def __init__(self, case):
        self.case = case

    @property
    def inputs(self):
        c = self.case
        return [c.tumor_dna, c.normal_dna, c.tumor_rna]

    @property
    def outputs(self):
        c = self.case
        return [c.tumor_dna_bam, c.normal_dna_bam, c.tumor_rna_bam]

    def _samples(self):
        """(raw src, normalized dst, modality) for the three samples — the one
        place the DNA/RNA split is declared."""
        c = self.case
        return [
            (c.tumor_dna,  c.tumor_dna_bam,  "dna"),
            (c.normal_dna, c.normal_dna_bam, "dna"),
            (c.tumor_rna,  c.tumor_rna_bam,  "rna"),
        ]

    def dry_check_inputs(self) -> None:
        for p in self.inputs:
            checks.require_nonempty(p)
            checks.require_ext(p, _RAW_EXTS)

    def dry_check_outputs(self) -> None:
        for p in self.outputs:
            checks.require_nonempty(p)
            checks.require_bgzf(p)  # TODO: also require a .bai index alongside

    def self_test(self) -> str | None:
        from .align_bwa_star import (
            classify, normalization_plan, parse_sam_header, needs_sort, contig_style,
        )
        try:
            # --- classification ---
            assert classify("x/tumor.bam") == "bam"
            assert classify("x/reads.fastq.gz") == "fastq"
            assert classify("x/aln.cram") == "cram"
            try:
                classify("x/notes.txt")
                return "1-input self_test failed: bad extension not caught"
            except ValueError:
                pass

            # --- aligned BAM (SEQC2 DNA MVP): sort + index only, no aligner ---
            bam_plan = normalization_plan("raw/t.bam", "out/t.bam", "dna")
            assert [s.action for s in bam_plan] == ["sort", "index"], bam_plan
            assert all(s.tool == "samtools" for s in bam_plan)

            # --- RNA FASTQ: splice-aware STAR, then sort + index ---
            rna_plan = normalization_plan("raw/r.fastq.gz", "out/r.bam", "rna", reference="ref")
            assert [s.tool for s in rna_plan] == ["STAR", "samtools", "samtools"], rna_plan
            # --- DNA FASTQ: contiguous bwa (NOT STAR) ---
            dna_plan = normalization_plan("raw/n.fastq.gz", "out/n.bam", "dna", reference="ref")
            assert dna_plan[0].tool == "bwa", dna_plan
            # aligning FASTQ without a reference must fail loudly
            try:
                normalization_plan("raw/r.fastq", "out/r.bam", "rna")
                return "1-input self_test failed: FASTQ w/o reference not caught"
            except ValueError:
                pass

            # --- header parser: sort-order + contig-style checks ---
            hdr = ("@HD\tVN:1.6\tSO:coordinate\n"
                   "@SQ\tSN:chr21\tLN:46709983\n@SQ\tSN:chr22\tLN:50818468\n")
            meta = parse_sam_header(hdr)
            assert meta["sort_order"] == "coordinate" and meta["contigs"] == ["chr21", "chr22"]
            assert needs_sort(hdr) is False
            assert needs_sort("@HD\tVN:1.6\tSO:unsorted\n") is True
            assert contig_style(["chr21"]) == "chr" and contig_style(["21"]) == "plain"
            assert contig_style(["chr1", "21"]) == "mixed"
        except AssertionError as e:  # noqa: BLE001
            return f"1-input self_test failed: {e}"
        return None

    def run(self) -> None:
        # assemble the concrete per-sample plan (our logic), then hand off to the
        # tools — deferred to Colab, so we fail loudly *with the plan* rather than
        # fabricate BAMs. MVP path: DNA arrives pre-aligned -> sort+index (needs no
        # reference); FASTQ alignment (RNA via STAR) would add `reference` here.
        from .align_bwa_star import classify

        commands: list[str] = []
        for src, dst, modality in self._samples():
            try:
                aligned = classify(src) in ("bam", "cram")
            except ValueError:
                aligned = False
            if aligned:
                commands += [s.command for s in normalization_plan(src, dst, modality)]
            else:
                commands.append(f"# {modality} FASTQ {src}: align (bwa/STAR) + sort + index — needs reference (Colab)")

        raise NotImplementedError(
            "1-input.run — execute normalization in Colab (bwa/STAR/samtools). "
            "Planned commands:\n  " + "\n  ".join(commands)
        )
