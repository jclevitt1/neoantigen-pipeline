# Approach: known genotype (published lookup)

The default typer — and the reason stage 2b runs **today** with no reads and no
tool. HLA type is germline, so for well-characterized benchmark cell lines it's
already been published; we look it up by `case.sample_id` instead of typing.

## The table (verified, sourced)

| sample | HLA-A | HLA-B | HLA-C |
|---|---|---|---|
| **HCC1395** | A\*29:02 (hom.) | B\*08:01, B\*45:01 | C\*06:02, C\*07:01 |
| **COLO829** | A\*01:01 (hom.) | B\*08:01, B\*40:02 | C\*03:04, C\*07:06 |

Source: **Cellosaurus** ([CVCL_1249](https://www.cellosaurus.org/CVCL_1249),
[CVCL_1137](https://www.cellosaurus.org/CVCL_1137)), citing **TCLP** (Scholtalbers
et al., *Genome Medicine* 2015, [PMID 26589293](https://pubmed.ncbi.nlm.nih.gov/26589293/)).
Both lines are homozygous at HLA-A → 5 distinct class-I alleles each. `…BL` normal
samples share the genotype (germline). Aliases (`HCC1395BL`, `COLO829BL`, spacing)
resolve to the canonical key.

## Why this is legitimate, not a cheat

The genotype is a real, independently-reported measurement — the same input
OptiType would reconstruct from reads. Using it lets the whole pipeline run
end-to-end on the demo Case now; swapping to `../optitype/` for an unknown patient
changes nothing downstream (same `hla.json` shape).

Adding a line: append `sample_id → [alleles]` to `KNOWN_GENOTYPES`, sourced from
that line's Cellosaurus HLA-typing field.
