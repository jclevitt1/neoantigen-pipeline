"""
Rule-based eval filters — the approach behind stage 5.

Three plain functions + their constants, kept separate from the Stage so they're
unit-testable with in-memory fixtures (no files). See README.md in this directory
for the thresholds' rationale.
"""
from __future__ import annotations

# Kyte-Doolittle hydropathy — mean over a peptide = GRAVY score.
_KD = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5, "E": -3.5,
    "G": -0.4, "H": -3.2, "I": 4.5, "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8,
    "P": -1.6, "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}
_GRAVY_MAX = 1.0     # above this, too hydrophobic to synthesize/dissolve reliably
_MAX_CYS = 1         # >=2 cysteines -> disulfide/aggregation risk
_CLONAL_CCF = 0.9    # CCF at/above this = clonal (present in ~all tumor cells)


def flag_autoimmunity(peptide: str, proteome_index: str) -> bool:
    """True (risky) if the peptide occurs verbatim in a normal self-protein.
    `proteome_index` is the proteome's sequences joined by a separator so a
    match can't span two proteins. MVP proxy — near-match (BLAST) is the TODO."""
    return peptide in proteome_index


def classify_clonality(ccf) -> str:
    try:
        ccf = float(ccf)
    except (TypeError, ValueError):
        return "unknown"
    return "clonal" if ccf >= _CLONAL_CCF else "subclonal"


def check_manufacturability(peptide: str) -> str:
    if not peptide:
        return "fail"
    gravy = sum(_KD.get(aa, 0.0) for aa in peptide) / len(peptide)
    if gravy > _GRAVY_MAX:
        return "fail"
    if peptide.count("C") > _MAX_CYS:
        return "fail"
    return "pass"


def load_proteome_index(proteome_fasta) -> str:
    """Concatenate proteome sequences, '|'-separated to block cross-protein hits."""
    seqs, cur = [], []
    with open(proteome_fasta) as fh:
        for line in fh:
            if line.startswith(">"):
                if cur:
                    seqs.append("".join(cur)); cur = []
            else:
                cur.append(line.strip())
    if cur:
        seqs.append("".join(cur))
    return "|".join(seqs)


def proteome_index_from_str(fasta_text: str) -> str:
    """In-memory twin of load_proteome_index, for self_test fixtures."""
    seqs, cur = [], []
    for line in fasta_text.splitlines():
        if line.startswith(">"):
            if cur:
                seqs.append("".join(cur)); cur = []
        else:
            cur.append(line.strip())
    if cur:
        seqs.append("".join(cur))
    return "|".join(seqs)
