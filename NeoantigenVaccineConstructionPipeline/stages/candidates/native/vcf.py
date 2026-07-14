"""
vcf.py — minimal reader for a VEP-annotated somatic VCF.

Just enough to feed windows.py: pull the per-transcript CSQ subfields for each
protein-altering variant. A VCF is line-oriented text, so this is plain string
parsing — no pysam. (The heavy lifting was VEP's, upstream in stage 2a.)

What we rely on VEP (+ the Wildtype protein plugin, as pVACseq uses) to have put
in the CSQ:
    SYMBOL | Feature | Consequence | Amino_acids (ref/alt) | Protein_position |
    WildtypeProtein
The CSQ column order is not fixed across VEP runs, so we read it from the
`##INFO=<ID=CSQ,...Format: ...>` header line rather than hardcoding positions.
"""
from __future__ import annotations

import re
from pathlib import Path

# consequences that change the protein sequence -> can yield a neoantigen.
# (frameshift/inframe indels need the Downstream plugin; MVP handles missense.)
PROTEIN_ALTERING = {"missense_variant"}


def _parse_csq_format(lines: list[str]) -> list[str]:
    """Extract the pipe-delimited CSQ subfield names from the header."""
    for line in lines:
        if line.startswith("##INFO=<ID=CSQ"):
            m = re.search(r"Format:\s*([^\">]+)", line)
            if m:
                return m.group(1).strip().split("|")
    raise ValueError("no ##INFO=<ID=CSQ ... Format: ...> header found in VCF")


def _info_field(info: str, key: str) -> str | None:
    """Pull one KEY=value out of the 8th (INFO) VCF column."""
    for part in info.split(";"):
        if part.startswith(key + "="):
            return part[len(key) + 1:]
    return None


def _tumor_vaf(fields: list[str]) -> str:
    """Best-effort allele fraction from FORMAT/sample columns (Mutect2 AF).

    Returns '' if absent — expression, not VAF, is the required tag; VAF is a
    passthrough that stage 5 uses as a clonality proxy when CCF isn't computed.
    """
    if len(fields) < 10:
        return ""
    fmt = fields[8].split(":")
    if "AF" not in fmt:
        return ""
    af_idx = fmt.index("AF")
    sample = fields[9].split(":")  # first sample column
    return sample[af_idx] if af_idx < len(sample) else ""


def parse_variants(lines: list[str]) -> list[dict]:
    """Parse VCF text (list of lines) into protein-altering variant dicts.

    One dict per (variant x protein-altering transcript) — a variant hitting
    several transcripts yields several, exactly as pVACseq treats them.
    """
    csq_cols = _parse_csq_format(lines)
    col = {name: i for i, name in enumerate(csq_cols)}
    required = ["SYMBOL", "Feature", "Consequence", "Amino_acids",
                "Protein_position", "WildtypeProtein"]
    missing = [c for c in required if c not in col]
    if missing:
        raise ValueError(f"CSQ format missing required subfields {missing}; has {csq_cols}")

    variants: list[dict] = []
    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.rstrip("\n").split("\t")
        info = fields[7]
        csq = _info_field(info, "CSQ")
        if csq is None:
            continue
        vaf = _tumor_vaf(fields)
        for transcript_csq in csq.split(","):
            v = transcript_csq.split("|")
            if col["Consequence"] >= len(v):
                continue
            consequence = v[col["Consequence"]]
            # a CSQ Consequence can be '&'-joined (e.g. missense&splice)
            if not (set(consequence.split("&")) & PROTEIN_ALTERING):
                continue
            aa = v[col["Amino_acids"]]           # 'G/D'
            if "/" not in aa:
                continue
            ref_aa, alt_aa = aa.split("/", 1)
            pos = v[col["Protein_position"]].split("-")[0].split("/")[0]  # '12' or '12-13'
            wt = v[col["WildtypeProtein"]]
            if not (pos and wt and alt_aa):
                continue
            variants.append({
                "gene": v[col["SYMBOL"]],
                "transcript": v[col["Feature"]],
                "consequence": consequence,
                "ref_aa": ref_aa,
                "alt_aa": alt_aa,
                "protein_position": pos,
                "wildtype": wt,
                "vaf": vaf,
            })
    return variants


def read_variants(path) -> list[dict]:
    """parse_variants() over a file on disk."""
    return parse_variants(Path(path).read_text().splitlines())
