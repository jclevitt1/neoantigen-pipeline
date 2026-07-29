"""
Stage 3 — Candidate generation.  (NATIVE; contract + orchestration)

Annotated somatic VCF -> mutant peptide windows (8-11mers), each tagged with RNA
expression so untranscribed mutations drop out. The window logic is ours and
lives under native/ (windows.py + vcf.py); expression is a pluggable seam
(native/expression.py) defaulting to a no-RNA placeholder. See
stages/candidates/README.md and native/README.md.
"""
from __future__ import annotations

import csv

from core import Stage
from .. import checks
from .native import vcf, windows
from .native.expression import DEFAULT_EXPRESSION, UNKNOWN_TPM

_REQUIRED_COLS = ["peptide", "tpm"]  # minimal contract; more added by later stages
_OUT_COLS = ["peptide", "wt_peptide", "tpm", "gene", "transcript", "protein_change", "length", "vaf"]


class CandidateStage(Stage):
    """Stage 3 - translate each protein-altering variant into the 8-11mer peptide
    windows that cover the mutated residue, each paired with its wild-type
    counterpart (so stage 4 can compute agretopicity) and tagged with expression."""
    name = "3-candidates"
    kind = "native"
    description = "Translate mutations into mutant peptides (8-11mers), tagged with RNA expression."

    def __init__(self, case, expression=None):
        self.case = case
        # pluggable expression tag; default needs no RNA (emits tpm='NA')
        self.expression = expression or DEFAULT_EXPRESSION()

    @property
    def inputs(self):
        # the VCF is always required; the expression source declares whether it
        # also needs the RNA BAM (placeholder -> none; featureCounts -> RNA BAM)
        return [self.case.somatic_vcf, *self.expression.required_inputs(self.case)]

    @property
    def outputs(self):
        return [self.case.candidates_tsv]

    def dry_check_inputs(self) -> None:
        checks.require_vcf(self.case.somatic_vcf)
        self.expression.dry_check(self.case)

    def dry_check_outputs(self) -> None:
        checks.require_tsv_columns(self.case.candidates_tsv, _REQUIRED_COLS)

    def self_test(self) -> str | None:
        try:
            # --- pure window logic ---
            # KRAS G12D over a WT snippet: ...MTEYKLVVVGAG G VGKSALT...
            wt = "MTEYKLVVVGAGGVGKSALT"
            mut = windows.apply_substitution(wt, 12, "G", "D")
            assert mut == "MTEYKLVVVGADGVGKSALT", mut          # residue 12 G->D
            covering = windows.windows_covering(mut, 11)        # 11 = 0-based index of the D
            assert covering, "no windows generated"
            assert all(len(p) in (8, 9, 10, 11) for p in covering)
            assert all("D" in p for p in covering)              # every candidate carries the mutation
            assert "VVGADGVGK" in covering                      # a 9mer straddling the mutation

            # --- ref-mismatch guard ---
            try:
                windows.apply_substitution(wt, 12, "A", "D")    # WT has G, not A
                return "3-candidates self_test failed: ref mismatch not caught"
            except ValueError:
                pass

            # --- VCF/CSQ parse -> variant -> peptides, end to end ---
            fixture = _FIXTURE_VCF.splitlines()
            variants = vcf.parse_variants(fixture)
            assert len(variants) == 1, variants
            v = variants[0]
            assert v["gene"] == "KRAS" and v["protein_position"] == "12"
            assert v["ref_aa"] == "G" and v["alt_aa"] == "D"
            rows = windows.peptides_from_variant(v)
            assert rows and all(r["protein_change"] == "G12D" for r in rows)
            assert all("D" in r["peptide"] for r in rows)
            # WT counterpart: same window, carries the original G where the mutant
            # has D, same length, so stage 4 can compute agretopicity (DAI).
            assert all(len(r["wt_peptide"]) == r["length"] for r in rows)
            assert all("D" not in r["wt_peptide"] and "G" in r["wt_peptide"] for r in rows)
        except AssertionError as e:  # noqa: BLE001
            return f"3-candidates self_test failed: {e}"
        return None

    def run(self) -> None:
        c = self.case
        tpm_min = getattr(self.expression, "tpm_min", 0.0)

        variants = vcf.read_variants(c.somatic_vcf)
        out_rows: list[dict] = []
        for v in variants:
            for row in windows.peptides_from_variant(v):
                tpm = self.expression.tpm_for(row["gene"], row["transcript"])
                # drop only when expression is a REAL number below threshold;
                # unknown (placeholder) always survives
                if isinstance(tpm, (int, float)) and tpm < tpm_min:
                    continue
                row["tpm"] = tpm if isinstance(tpm, (int, float)) else UNKNOWN_TPM
                out_rows.append(row)

        with open(c.candidates_tsv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=_OUT_COLS, delimiter="\t", extrasaction="ignore")
            w.writeheader()
            w.writerows(out_rows)


# A tiny VEP-annotated VCF fixture: one KRAS G12D missense with the WT protein
# snippet the Wildtype plugin would attach. Used only by self_test.
_FIXTURE_VCF = (
    '##fileformat=VCFv4.2\n'
    '##INFO=<ID=CSQ,Number=.,Type=String,Description="Format: '
    'SYMBOL|Feature|Consequence|Amino_acids|Protein_position|WildtypeProtein">\n'
    "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tTUMOR\n"
    "chr12\t25245350\t.\tC\tT\t.\tPASS\t"
    "CSQ=KRAS|ENST00000311936|missense_variant|G/D|12|MTEYKLVVVGAGGVGKSALT"
    "\tGT:AF\t0/1:0.31\n"
)
