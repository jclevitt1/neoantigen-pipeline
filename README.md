# Neoantigen Vaccine Design Pipeline

End-to-end replication of a personalized cancer-vaccine *design* pipeline:
matched tumor/normal sequencing → somatic variants → neoantigen candidates →
immunogenicity ranking → vaccine construct.

**Scope boundary (honest):** this designs a vaccine construct in silico. It does
NOT validate efficacy — that requires wet-lab immunogenicity assays (ELISpot,
tetramer) or animal models. The pipeline hands off exactly where silicon hands
off to the lab.

## Architecture

One abstraction: a **Stage** is a typed-file transform.

    Stage: declared input files -> run() -> declared output files
           (skip if outputs exist and inputs unchanged)

The pipeline is a **DAG** of Stages (not a linear state machine — branches 2a/2b
are independent and run in parallel). A **Case** bundles one patient's inputs so
swapping HCC1395 -> COLO829 is one object.

Two flavors behind the one interface:
- **Adapter stages** (0,1,2,3,5): wrap an existing tool; thin plumbing + format.
- **Native stages** (4,6): our code. Stage 4 = the Model A/B ranker
  (`../immunogenerative_logistic_abtest`).

## Stages (DAG)

| # | Stage        | In                              | Out                        | Kind    |
|---|--------------|---------------------------------|----------------------------|---------|
| 0 | Fetch        | accession IDs                   | tumor/normal/RNA BAM       | adapter |
| 1 | Align        | FASTQ (skipped if BAM provided) | BAM                        | adapter |
| 2a| Variant call | tumor+normal BAM                | somatic VCF (annotated)    | adapter |
| 2b| HLA type     | normal BAM                      | HLA alleles (JSON)         | adapter |
| 3 | Candidates   | annotated VCF + RNA BAM         | peptide TSV (expr-tagged)  | adapter |
| 4 | Rank         | peptide TSV + HLA               | peptide TSV (+scores)      | native  |
| 6 | Eval filters | peptide TSV + proteome          | peptide TSV (+flags)       | native  |
| 5 | Construct    | top-N peptides                  | construct FASTA + JSON     | adapter |

Dataflow note: 6 gates 5 (filter, then build survivors). The peptide TSV is one
table traveling 3->4->6, gaining columns at each step.

## Tests
- Native stages (4,6): real unit tests, fixtures, hard assertions.
- Adapter stages: contract/smoke tests (well-formed output from tiny input) —
  we don't re-verify the wrapped tool's correctness.

## Data sources (public, no approval needed to start)
- HCC1395 / HCC1395BL — matched breast tumor/normal (SEQC2 benchmark).
- COLO829 / COLO829BL — matched melanoma tumor/normal (second case).
- TCGA open-tier MAFs — thousands of patients, downstream breadth.
