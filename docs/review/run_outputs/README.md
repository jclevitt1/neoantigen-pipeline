# Committed run artifacts

Every file the pipeline produced on a real end-to-end run, committed so the documented
result can be checked against actual output rather than taken on trust.

## Provenance

- **Run date:** 2026-07-28, locally on an Apple-Silicon Mac (not Colab).
- **Code:** the commit this directory was added in — no local modifications.
- **Entry point:** `NeoantigenVaccineConstructionPipeline.demos.component_test.run_component_test`
- **Input variants:** the curated real-oncogenic-hotspot panel in
  [`curated.py`](../../../NeoantigenVaccineConstructionPipeline/stages/variants/fixture/curated.py)
  — KRAS G12D/G12V, BRAF V600E, TP53 R175H, PIK3CA H1047R, EGFR L858R. These are real
  mutations on real human proteins, hand-picked; **no claim is made that any tumour
  carries this exact set.**
- **HLA:** `DEMO_HLA_PANEL`, a 6-allele class-I genotype **deliberately seeded** with the
  published restricting alleles for those hotspots. That makes the KRAS G12D →
  HLA-C\*08:02 result a **positive control**, not a discovery.
- **Proteome:** Swiss-Prot human, 20,431 reviewed proteins (UniProt, fetched at run time).
- **Predictor:** MHCflurry 2.2.1, `models_class1_presentation`.

## Files

| File | What it is |
|------|-----------|
| `somatic.annotated.vcf` | stage 2a — the curated variants written as an annotated VCF |
| `hla.json` | stage 2b — the class-I genotype used |
| `candidates.tsv` | stage 3 — 228 peptide windows (8–11mers) covering the mutations |
| `ranked.tsv` | stage 4 — presentation gate + recognition composite, sorted |
| `filtered.tsv` | stage 5 — plus autoimmunity / clonality / manufacturability flags |
| `construct.fasta` | stage 6 — the vaccine construct, amino acid + nucleotide ORF |
| `construct.json` | stage 6 — the recipe, including what was deliberately omitted |

## Reading the result

`ranked.tsv` is decoded column by column in
[`../output_glossary.md`](../output_glossary.md). Top of the table:

| peptide | gene | change | allele | presentation | tier | immunogenicity |
|---------|------|--------|--------|-------------:|------|---------------:|
| GADGVGKSAL | KRAS | G12D | HLA-C\*08:02 | 0.950 | pass | 3.116 |
| ARHGGWTTKM | PIK3CA | H1047R | HLA-C\*07:01 | 0.838 | pass | 2.203 |

## Two honest observations about `construct.fasta`

Recorded here rather than quietly left for a reader to notice:

1. **Three of the seven selected peptides have negative immunogenicity**
   (ITDFGRAKL −0.054, VVVGADGVGK −0.139, KITDFGRAK −0.546). A negative score means the
   mutation made the peptide bind *worse* than its wild-type counterpart — by this
   pipeline's own scoring, an actively bad target. `select_survivors` currently takes
   the top N survivors with no score floor, so they are included. They should not be.
2. **Coverage is redundant.** Seven peptides cover only four distinct mutations
   (EGFR L858R appears three times, KRAS G12D twice) because overlapping windows of one
   mutation compete for slots. A real construct maximizes *mutation* coverage.

Both are single-function fixes in
[`string_of_beads/builder.py`](../../../NeoantigenVaccineConstructionPipeline/stages/construct/string_of_beads/builder.py)
and are open work, not design intent.
