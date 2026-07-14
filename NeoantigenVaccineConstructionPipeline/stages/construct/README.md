# Stage 6 — Construct

**Job:** take the shortlist of surviving peptides and assemble them into one
manufacturable vaccine construct.

## The "string of beads"

A modern neoantigen vaccine strings many epitopes into a single molecule:

```
EPITOPE_1 — linker — EPITOPE_2 — linker — ... — EPITOPE_n
```

Then, for an mRNA vaccine, that amino-acid string is **reverse-translated** into a
nucleotide sequence the cell can express. One construct = one manufacturing run;
the cell's proteasome later chops it back into the individual epitopes for display.

## Delivery formats (context)

The chosen peptides can become a vaccine several ways — synthetic long peptides,
**mRNA** (the current frontrunner: Moderna mRNA-4157, BioNTech autogene
cevumeran), DNA, or dendritic-cell. This stage outputs an mRNA-style string.

## Design requirements (what a real construct must satisfy)

1. **Payload cap** — you can only fit so many (mRNA-4157 ~34, cevumeran ~20). Pick
   top N. → the ranking + eval stages earn their keep here.
2. **Cleavable linkers** — spacers must let the proteasome liberate each epitope.
   We use `AAY` (favors MHC-I cleavage).
3. **Avoid junctional neoepitopes** — the seam between two peptides can spell a
   spurious new epitope. *(Not handled in MVP — see below.)*
4. **Manufacturability of the whole molecule** — codon optimization, GC content,
   secondary structure, no cryptic splice/poly-A signals.
5. **Trafficking signals** + **CD4/MHC-II epitopes** for a stronger, sustained
   response. *(Not handled in MVP.)*

## MVP scope — honest boundary

**Built (real):** survivor selection (stage-5 gate, best-first by immunogenicity,
clonal tiebreak, top N) → `AAY`-linked polypeptide → codon-optimized nucleotide ORF
→ `construct.fasta` (AA + NT records) + `construct.json` (full recipe).

**Deliberately omitted** (recorded in the recipe's `omitted_for_mvp`, and in
`string_of_beads/README.md`): junctional-epitope minimization, MHC-II epitopes,
signal/trafficking tags, the mRNA scaffold (cap/UTRs/poly-A/stop), nucleoside
modification. Each is its own project; the output is a *real, inspectable* construct,
not a manufacturing-ready design.

## I/O contract

| | |
|---|---|
| **Inputs** | `filtered.tsv` (from stage 5) |
| **Outputs** | `construct.fasta` (AA + NT), `construct.json` (recipe) |
| **Dry checks** | input TSV has `peptide`; outputs valid FASTA + JSON |

Auto-runs a `self_test` on build (survivor selection + assembly + codon length).

## Approaches

- [`string_of_beads/`](string_of_beads/) — linker concatenation + codon optimization.
