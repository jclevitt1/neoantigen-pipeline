# Approach: String of beads (mRNA-style)

Concatenate the surviving epitopes with cleavable linkers, then reverse-translate
to a nucleotide ORF. Pure functions in `builder.py`.

## Pipeline

1. **`select_survivors`** — keep rows that passed the stage-6 gate
   (`autoimmunity_flag == False` **and** `manufacturability == "pass"`), sort
   best-first by `immunogenicity` (clonal preferred as tiebreak), cap at
   `DEFAULT_MAX_PEPTIDES` (20).
2. **`assemble_peptide`** — join with the `AAY` linker *between* epitopes (not at
   the ends). AAY promotes proteasomal cleavage so each epitope is liberated.
3. **`reverse_translate`** — one **human high-frequency codon** per residue
   (`_CODON`). Nucleotide length is always `3 ×` the amino-acid length.

## Key constants
- `DEFAULT_LINKER = "AAY"`
- `DEFAULT_MAX_PEPTIDES = 20`
- `_CODON` — preferred codon table (swap for a species/expression-system table).

## Honest omissions (`OMITTED` in builder.py)

Junctional-epitope minimization, MHC-II epitopes, signal/trafficking domains, the
full mRNA scaffold (5' cap, UTRs, poly-A, stop codon), and nucleoside modification.
The recipe JSON echoes these under `omitted_for_mvp` so the output never reads as
manufacturing-ready.

## Upgrade paths
- **Junctional check:** after ordering, scan each linker seam for peptides that
  bind the patient's alleles; reorder to minimize.
- **Codon optimization:** replace the static table with CAI-aware optimization +
  secondary-structure/GC constraints.
