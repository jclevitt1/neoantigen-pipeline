"""
Stage 2a — Somatic variant calling ("the diff").  (adapter; contract + orchestration)

Tumor DNA MINUS normal DNA -> mutations unique to the cancer, annotated with
protein consequences (the CSQ stage 3 reads). The concrete caller+annotator is a
pluggable VariantSource (base.py), like stage 4's Ranker / 2b's HlaTyper:

  - default  Mutect2VepCaller  — real Mutect2 + VEP; declares BAM+reference inputs;
             execution defers to Colab (somatic calling can't be faked from nothing).
  - opt-in   FixtureVariants   — a labelled didactic variant; zero inputs; runs today
             for a tool-free end-to-end wiring run.

The one piece we own and test now is the VCF *writer* (base.write_annotated_vcf):
self_test round-trips it through stage 3's own parser, proving the 2a -> 3 hand-off
is byte-compatible without any external tool.

NOTE: 2a and 2b are two INDEPENDENT branches off the normalized BAMs — separate
stages precisely so the DAG can run them in parallel later. 2a reads tumor+normal.
"""
from __future__ import annotations

from core import Stage
from .. import checks
from .base import VariantSource
from .mutect2_vep import Mutect2VepCaller

DEFAULT_SOURCE = Mutect2VepCaller


class VariantCallStage(Stage):
    """Stage 2a - the tumor-minus-normal diff: somatic variants called against the
    matched normal, annotated with protein consequences and the wild-type protein
    (stage 3 needs the WT sequence to build mutant/WT peptide pairs)."""
    name = "2a-variants"
    kind = "adapter"
    description = "The 'diff': somatic variants (tumor - normal), annotated with protein consequences."

    def __init__(self, case, source: VariantSource | None = None):
        self.case = case
        # pluggable seam; default is the real Mutect2+VEP path (deferred to Colab)
        self.source = source or DEFAULT_SOURCE()

    @property
    def inputs(self):
        # only the chosen source's real edges (default: tumor+normal BAM + reference;
        # FixtureVariants: none)
        return list(self.source.required_inputs(self.case))

    @property
    def outputs(self):
        return [self.case.somatic_vcf]

    def dry_check_inputs(self) -> None:
        self.source.dry_check(self.case)

    def dry_check_outputs(self) -> None:
        checks.require_vcf(self.case.somatic_vcf)
        # the annotated VCF must advertise CSQ, or stage 3 has nothing to read
        with open(self.case.somatic_vcf) as fh:
            if "##INFO=<ID=CSQ" not in fh.read():
                raise ValueError(f"{self.case.somatic_vcf}: no CSQ annotation header")

    def self_test(self) -> str | None:
        import tempfile
        from pathlib import Path

        from .fixture import DEMO_VARIANTS
        from .base import write_annotated_vcf, CSQ_FIELDS
        # stage 3's reader is the other end of this contract — test against IT,
        # not a private copy, so drift can't hide.
        from ..candidates.native import vcf as s3_vcf
        from ..candidates.native import windows as s3_windows

        try:
            with tempfile.TemporaryDirectory() as d:
                out = Path(d) / "somatic.annotated.vcf"
                write_annotated_vcf(DEMO_VARIANTS, out)
                text = out.read_text()

                assert text.startswith("##fileformat=VCF"), "not a VCF"
                assert "##INFO=<ID=CSQ" in text, "no CSQ header"
                for name in CSQ_FIELDS:
                    assert name in text, f"CSQ Format missing {name}"

                # --- round-trip: 2a writer -> stage 3 reader recovers the record ---
                variants = s3_vcf.read_variants(out)
                assert len(variants) == 1, variants
                v = variants[0]
                assert v["gene"] == "KRAS" and v["transcript"] == "ENST00000311936"
                assert v["ref_aa"] == "G" and v["alt_aa"] == "D"
                assert v["protein_position"] == "12"
                assert v["vaf"] == "0.31"

                # --- and it yields the expected KRAS G12D peptides downstream ---
                rows = s3_windows.peptides_from_variant(v)
                assert rows and all(r["protein_change"] == "G12D" for r in rows)
                assert all("D" in r["peptide"] for r in rows)
                assert "VVGADGVGK" in {r["peptide"] for r in rows}
        except AssertionError as e:  # noqa: BLE001
            return f"2a-variants self_test failed: {e}"
        return None

    def run(self) -> None:
        self.source.produce(self.case, self.case.somatic_vcf)
