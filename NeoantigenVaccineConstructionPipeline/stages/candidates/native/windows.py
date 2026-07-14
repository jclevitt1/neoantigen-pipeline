"""
windows.py — the pure heart of stage 3: turn a mutant protein + the mutated
position into the neoantigen candidate peptides.

No I/O, no external tools, no bio libraries — just string surgery. Everything
here is deterministic and hard-tested from the stage's self_test, because this
is the part we actually *own* (the rest of the stage is parsing + orchestration).

Two ideas only:
  1. Build the mutant protein by substituting one residue into the wild-type.
  2. Emit every k-mer (k in 8..11) that COVERS the mutated residue. A window that
     doesn't touch the mutation is identical to a normal human peptide -> useless.
"""
from __future__ import annotations

# MHC-I physically holds 8-11 residues; 9 is by far the most common.
DEFAULT_LENGTHS = (8, 9, 10, 11)


def apply_substitution(wildtype: str, position1: int, ref_aa: str, alt_aa: str) -> str:
    """Return the mutant protein: `wildtype` with residue at `position1`
    (1-based, as VEP reports Protein_position) changed ref_aa -> alt_aa.

    The ref_aa check is a cheap guard that the annotation and the protein agree —
    a mismatch means the VCF and the transcript sequence are out of sync, which
    would silently produce garbage peptides.
    """
    idx = position1 - 1
    if not (0 <= idx < len(wildtype)):
        raise ValueError(f"protein_position {position1} out of range for length {len(wildtype)}")
    if ref_aa and wildtype[idx] != ref_aa:
        raise ValueError(
            f"ref mismatch at position {position1}: protein has "
            f"{wildtype[idx]!r}, annotation says {ref_aa!r}"
        )
    return wildtype[:idx] + alt_aa + wildtype[idx + 1:]


def windows_covering_spans(seq: str, index0: int, lengths=DEFAULT_LENGTHS):
    """Like `windows_covering`, but yields `(start, k, peptide)` spans so a caller
    can slice the SAME coordinates out of a parallel sequence (e.g. the wild-type
    protein, to build the WT counterpart of each mutant window for agretopicity).

    Dedup is on the peptide string, matching `windows_covering`.
    """
    if not (0 <= index0 < len(seq)):
        raise ValueError(f"index {index0} out of range for length {len(seq)}")
    seen: set[str] = set()
    n = len(seq)
    for k in lengths:
        # start must satisfy: start <= index0,  start >= index0-k+1,
        # start >= 0,  start <= n-k  (so the window fits).
        lo = max(0, index0 - k + 1)
        hi = min(index0, n - k)
        for start in range(lo, hi + 1):
            pep = seq[start:start + k]
            if pep not in seen:
                seen.add(pep)
                yield start, k, pep


def windows_covering(seq: str, index0: int, lengths=DEFAULT_LENGTHS) -> list[str]:
    """Every k-mer of the given lengths that contains position `index0` (0-based).

    A window [start, start+k) covers index0 iff  start <= index0 < start+k.
    Returns unique peptides, ordered by (length, start) — deterministic. Windows
    that would run off either end of `seq` are simply skipped.
    """
    return [pep for _, _, pep in windows_covering_spans(seq, index0, lengths)]


def peptides_from_variant(variant: dict, lengths=DEFAULT_LENGTHS) -> list[dict]:
    """Expand one annotated missense variant into candidate peptide rows.

    `variant` is what native/vcf.py yields per protein-altering transcript:
        gene, transcript, wildtype (protein), protein_position (1-based),
        ref_aa, alt_aa, and optional passthrough fields (e.g. vaf).
    Returns one dict per candidate peptide, carrying the peptide plus the
    provenance a human (or stage 5) needs to trace it back to its mutation.
    """
    wildtype = variant["wildtype"]
    mutant = apply_substitution(
        wildtype, int(variant["protein_position"]),
        variant.get("ref_aa", ""), variant["alt_aa"],
    )
    mut_index0 = int(variant["protein_position"]) - 1
    change = f"{variant.get('ref_aa','')}{variant['protein_position']}{variant['alt_aa']}"

    rows: list[dict] = []
    for start, k, pep in windows_covering_spans(mutant, mut_index0, lengths):
        # A single substitution leaves the protein length unchanged, so the SAME
        # [start, start+k) window on the wild-type protein is the tolerized
        # counterpart peptide — differing only at the mutated residue. Stage 4
        # scores both to get agretopicity (DAI = binding_WT / binding_MT).
        rows.append({
            "peptide": pep,
            "wt_peptide": wildtype[start:start + k],
            "gene": variant.get("gene", ""),
            "transcript": variant.get("transcript", ""),
            "protein_change": change,
            "length": k,
            # passthrough for downstream stages (eval reads vaf as a ccf proxy)
            "vaf": variant.get("vaf", ""),
        })
    return rows
