# Approach: Rule-based filters

Three plain functions in `filters.py`, each with an explicit, tunable threshold.
Chosen for transparency — every verdict is explainable from the sequence/number.

| Filter | Rule | Constant | Honest limitation |
|---|---|---|---|
| **autoimmunity** | peptide is an **exact substring** of the human proteome → risky | — | misses **near**-matches (1–2 mismatch mimics); real fix = BLAST |
| **clonality** | `CCF ≥ 0.9` → `clonal`, else `subclonal`; non-numeric → `unknown` | `_CLONAL_CCF = 0.9` | flat cutoff; ignores CCF confidence intervals / tumor purity |
| **manufacturability** | fail if **GRAVY > 1.0** (too hydrophobic) or **>1 cysteine** | `_GRAVY_MAX`, `_MAX_CYS` | crude; real synthesis has many more rules (charge, length, motifs) |

**GRAVY** = mean Kyte-Doolittle hydropathy over the peptide. Positive = hydrophobic;
very hydrophobic peptides aggregate and resist synthesis/dissolution.

These functions are file-free on purpose, so `EvalStage.self_test()` exercises them
with in-memory fixtures on every build.

**Upgrade path:** swap the exact-match autoimmunity check for a BLAST near-match
against the human proteome — that's where most real cross-reactivity hides.
