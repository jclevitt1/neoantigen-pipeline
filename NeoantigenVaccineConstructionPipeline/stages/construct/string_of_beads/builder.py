"""
String-of-beads construct builder — the approach behind stage 6.

Pure functions (no file I/O) so they're unit-testable: pick survivors, concatenate
with cleavable linkers, reverse-translate to a nucleotide ORF. See README.md here
for the design and its (many) honest omissions.
"""
from __future__ import annotations

DEFAULT_LINKER = "AAY"     # favors proteasomal cleavage between MHC-I epitopes
DEFAULT_MAX_PEPTIDES = 20  # practical payload cap (cf. autogene cevumeran ~20)

# Human high-frequency codon per amino acid (a simple codon-optimization table).
_CODON = {
    "A": "GCC", "R": "CGC", "N": "AAC", "D": "GAC", "C": "TGC", "E": "GAG",
    "Q": "CAG", "G": "GGC", "H": "CAC", "I": "ATC", "L": "CTG", "K": "AAG",
    "M": "ATG", "F": "TTC", "P": "CCC", "S": "AGC", "T": "ACC", "W": "TGG",
    "Y": "TAC", "V": "GTG",
}

# Production elements a real construct would add — deliberately out of MVP scope.
OMITTED = [
    "junctional-epitope minimization (linker/order optimization)",
    "MHC-II (CD4 helper) epitopes",
    "N-terminal signal peptide + C-terminal MHC-trafficking domain",
    "mRNA scaffold: 5' cap, 5'/3' UTRs, poly-A tail, stop codon",
    "nucleoside modification (N1-methylpseudouridine)",
]


def _passes_presentation(row: dict) -> bool:
    """If a stage-4 presentation tier is recorded, require it to be 'pass'.
    Rows without a `tier` column (minimal fixtures) are not gated here — so this
    stays a no-op for callers that don't carry presentation info."""
    tier = str(row.get("tier", "")).strip().lower()
    return tier in ("", "pass")


def _is_survivor(row: dict) -> bool:
    """Passed the stage-5 gate (not autoimmune AND manufacturable) AND — if a
    stage-4 presentation tier is present — cleared the presentation gate. The tier
    guard stops the construct from padding itself toward max_peptides with
    gated-out `low-presentation` peptides that recognition scoring never applied to
    (their immunogenicity is NaN/stale). A vaccine peptide that won't be displayed
    on MHC is not a vaccine peptide."""
    auto = str(row.get("autoimmunity_flag", "")).strip().lower()
    manuf = str(row.get("manufacturability", "")).strip().lower()
    return (
        auto in ("false", "0", "")
        and manuf == "pass"
        and _passes_presentation(row)
    )


def _immunogenicity(row: dict) -> float:
    try:
        return float(row.get("immunogenicity", 0.0))
    except (TypeError, ValueError):
        return 0.0


def select_survivors(rows, max_peptides=DEFAULT_MAX_PEPTIDES) -> list[dict]:
    """Survivors, best-first by immunogenicity (clonal preferred as tiebreak),
    capped at max_peptides."""
    survivors = [r for r in rows if _is_survivor(r)]
    survivors.sort(key=lambda r: (
        -_immunogenicity(r),
        0 if str(r.get("clonality", "")).strip().lower() == "clonal" else 1,
    ))
    return survivors[:max_peptides]


def assemble_peptide(peptides: list[str], linker: str = DEFAULT_LINKER) -> str:
    """Concatenate epitopes with linkers between them (not at the ends)."""
    return linker.join(peptides)


def reverse_translate(aa_seq: str, codon: dict = _CODON) -> str:
    """Amino-acid string -> nucleotide ORF using one preferred codon per residue."""
    out = []
    for aa in aa_seq:
        if aa not in codon:
            raise ValueError(f"no codon for residue {aa!r} in {aa_seq!r}")
        out.append(codon[aa])
    return "".join(out)


def build_construct(rows, max_peptides=DEFAULT_MAX_PEPTIDES,
                    linker: str = DEFAULT_LINKER) -> dict:
    """rows (from filtered.tsv) -> the construct recipe. Returns a dict; the Stage
    turns it into construct.fasta + construct.json."""
    chosen = select_survivors(rows, max_peptides)
    peptides = [r.get("peptide", "") for r in chosen]
    aa = assemble_peptide(peptides, linker)
    nt = reverse_translate(aa) if aa else ""
    return {
        "n_peptides": len(peptides),
        "peptides": peptides,
        "linker": linker,
        "order": "immunogenicity_desc (clonal-preferred tiebreak)",
        "codon_table": "human_high_freq",
        "construct_aa": aa,
        "construct_nt": nt,
        "omitted_for_mvp": OMITTED,
    }
