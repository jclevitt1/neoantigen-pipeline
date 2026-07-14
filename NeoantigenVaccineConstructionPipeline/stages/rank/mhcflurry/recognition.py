"""
recognition.py — the pure Axis-2 (immunogenicity / recognition) math.

No I/O, no MHCflurry, no external libraries — just the functions that turn
binding numbers + sequences into the recognition features TESLA and Luksza
identified. Kept pure so they're unit-testable from the stage's self_test (the
MHCflurry binding calls, which need the wet package, live in binding.py).

Two axes, per docs/ranking_methodology.md:
  - Axis 1 (presentation) is a binding problem, answered by binding.py.
  - Axis 2 (recognition) is THIS file: given a peptide is presented, will a T
    cell respond? Encoded as agretopicity (DAI), dissimilarity-to-self, and
    optional foreignness, combined by the Luksza quality composite.
"""
from __future__ import annotations

from math import exp, log

_EPS = 1e-3  # floor for logs / ratios so a zero never blows up the composite


# --------------------------------------------------------------------------- #
# Axis-2 features
# --------------------------------------------------------------------------- #
def agretopicity(mut_affinity, wt_affinity):
    """Differential Agretopicity Index (DAI) = Kd_WT / Kd_MT (Luksza amplitude A).

    Affinities are nM (LOWER = stronger binding), so DAI > 1 means the mutant
    binds MORE strongly than its wild-type counterpart — i.e. the mutation
    created a newly-presented epitope the thymus never tolerized. Returns None
    if either affinity is missing/degenerate (caller decides how to handle).
    """
    mut_affinity = _num(mut_affinity)
    wt_affinity = _num(wt_affinity)
    if mut_affinity is None or wt_affinity is None or mut_affinity <= 0:
        return None
    return wt_affinity / mut_affinity


def dissimilarity_to_self(peptide: str, proteome_index: str):
    """Selfness distance C (Luksza 2022): how foreign the peptide looks vs self.

    MVP binary proxy, mirroring the stage-5 autoimmunity check: 0.0 if the
    peptide occurs verbatim in a normal human protein (fully self → tolerized),
    else 1.0 (novel surface). The true metric is a nearest-neighbour BLOSUM /
    BLAST distance to the proteome — that's the TODO (see README). Returns None
    if no proteome index was supplied (term simply drops out of the composite).
    """
    if not proteome_index:
        return None
    return 0.0 if peptide in proteome_index else 1.0


def foreignness(peptide: str, iedb_epitopes, k: float = 4.87, a: float = 26.0,
                align=None):
    """Recognition potential R (Luksza 2017): similarity to KNOWN immunogenic
    epitopes, as a TCR cross-reactivity prior.

        Z = sum_e exp(-k * (a - s(peptide, e))) ;  R = Z / (1 + Z)

    where s is an alignment score against each IEDB positive epitope `e`, passed
    through the steep sigmoid (k ≈ 4.87) Luksza fit. Dormant by default: returns
    None when `iedb_epitopes` is empty, so the composite falls back to R = 1.
    Supply the IEDB immunogenic set (and optionally a BLOSUM aligner) to enable.
    """
    if not iedb_epitopes:
        return None
    align = align or _ungapped_identity
    z = 0.0
    for e in iedb_epitopes:
        z += exp(-k * (a - align(peptide, e)))
    return z / (1.0 + z)


# --------------------------------------------------------------------------- #
# The Luksza quality composite  (Q = R * D,  D = log A + log C)
# --------------------------------------------------------------------------- #
def luksza_quality(agreto, dissimilarity=None, foreign=None):
    """Neoantigen quality Q = R * D,  D = log(A) + log(C)  (Luksza 2017/2022).

      A = agretopicity (amplitude; how much better the mutant binds than WT)
      C = dissimilarity-to-self (selfness distance; default 1.0 if unknown)
      R = foreignness / recognition prior (default 1.0 if unknown → Q = D)

    Higher Q = better candidate (used as the best-first sort key). Returns None
    if agretopicity is unavailable (nothing to rank on). Note Q can be negative
    when A or C < 1 — that's fine, it's an ordering, not a probability.
    """
    a = _num(agreto)
    if a is None:
        return None
    A = max(a, _EPS)
    C = max(_num(dissimilarity) if dissimilarity is not None else 1.0, _EPS)
    D = log(A) + log(C)
    R = _num(foreign) if foreign is not None else 1.0
    return R * D


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def load_proteome_index(proteome_fasta) -> str:
    """Concatenate proteome sequences, '|'-separated so a self-match can't span
    two proteins. (Local copy so stage 4 doesn't import stage 5's internals.)"""
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


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f


def _ungapped_identity(pep: str, epitope: str) -> float:
    """Trivial default aligner: best ungapped identity count over equal-length
    frames. A placeholder so `foreignness` is runnable without BLOSUM; swap in a
    real Smith-Waterman/BLOSUM62 scorer for production (see README)."""
    if not pep or not epitope:
        return 0.0
    short, long = (pep, epitope) if len(pep) <= len(epitope) else (epitope, pep)
    best = 0
    for off in range(len(long) - len(short) + 1):
        best = max(best, sum(a == b for a, b in zip(short, long[off:])))
    return float(best)
