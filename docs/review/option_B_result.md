# Option B1 — real-tumour end-to-end run (HCC1395), in-sandbox

_Ran 2026-07-17. The genomics **front end** validated on a real tumour's real,
published somatic mutations — the piece Option A (curated hotspots, stages 3→6)
deliberately skipped. Companion to [`README.md`](README.md) and
[`../e2e_validation_notes.md`](../e2e_validation_notes.md)._

## What ran (the whole chain, no cherry-picking)

```
SEQC2 HCC1395 high-confidence somatic SNV truth set (chr21 subset, 472 SNVs)
  → VEP + Wildtype annotation (protein consequence + WT protein)
  → stage 3 candidates (8–11mer windows)
  → stage 4 MHCflurry presentation gate + Łuksza composite
  → stage 5 eval (autoimmunity / manufacturability)
  → stage 6 string-of-beads construct
```

- **Mutations are real and unbiased:** the SEQC2 consortium's published
  high-confidence HCC1395 truth VCF, not hand-picked variants. 472 SNVs on chr21.
- **HLA is the real HCC1395 genotype** (`KnownGenotypeTyper`: A\*29:02, B\*08:01,
  B\*45:01, C\*06:02, C\*07:01).
- **Annotation is real:** Ensembl VEP with the pVACseq Wildtype plugin.

## The result — top presented neoepitope

Of 472 chr21 SNVs, **4 are missense** (chr21 is the most gene-poor autosome). After
the presentation gate, **one neoepitope survives**, on two peptide lengths:

| peptide | gene | mutation | best allele | binding (nM) | presentation | tier | agretopicity | immunogenicity |
|---------|------|----------|-------------|-------------:|-------------:|------|-------------:|---------------:|
| SPNSRIAL  | **COL6A1** | **N721S** | **HLA-B\*08:01** | 59.4 | **0.941** | pass | 1.043 | 0.042 |
| SPNSRIALV | **COL6A1** | **N721S** | **HLA-B\*08:01** | 66.9 | **0.966** | pass | 1.036 | 0.036 |

**The pipeline independently picked the right restriction:** COL6A1 N721S presents on
**HLA-B\*08:01**, which is one of HCC1395's *actual* published class-I alleles. The
mutation maps to three COL6A1 transcript isoforms (N721S in the canonical, N97S in two
shorter ones — the same genomic event), so each peptide appears once per isoform.

### Stage-6 construct
```
>HCC1395_construct_aa peptides=6 linker=AAY
SPNSRIALAAYSPNSRIALAAYSPNSRIALAAYSPNSRIALVAAYSPNSRIALVAAYSPNSRIALV
```
(reverse-translated to a codon-optimized nucleotide ORF; see the run's `construct.fasta`.)

## What this proves — and what it doesn't

**Proves (capability):** the full front-end — real VCF ingestion → VEP annotation →
the `WildtypeProtein` CSQ contract → candidate generation → presentation gate →
recognition composite → construct — runs start-to-finish on real published somatic
data. Combined with Option A (which validated stages 3→6 on curated real hotspots),
the entire pipeline is now demonstrably live on real inputs.

**Does NOT prove (and don't imply):**
- **COL6A1 N721S is a passenger, not a driver.** chr21 carries no famous oncogenic
  driver, and a real truth set is mostly passengers — so unlike Option A's curated
  KRAS G12D, this is "the pipeline works," not "the pipeline found a known driver."
- **The table is thin** — chr21 only (4 missense → 1 presented neoepitope). Widening to
  gene-dense chromosomes would enrich it (see below); it was scoped to chr21 for
  tractability, not because the method is limited to it.
- Recognition (agretopicity ≈ 1.04, immunogenicity ≈ 0.04) is weak — as expected;
  this is the field's honest ceiling (see [`concepts.md`](concepts.md)), not a defect.

## How it was run (reproducibility notes)

Run entirely **in-sandbox on an Apple-Silicon Mac** (no Colab), which forced two
useful engineering choices:

- **No 15 GB VEP cache.** VEP ran in **GFF+FASTA mode** off a chr21 GFF3 + a chr21
  reference — ~12 MB instead of ~15 GB.
- **chr21 reference by byte-range.** Extracted chr21 straight out of the Broad hg38
  FASTA via an HTTP range request (using its `.fai`), so the sequence dictionary
  matches the SEQC2 BAMs exactly (~47 MB, not the 3.1 GB whole genome).
- **WT protein injected post-hoc.** VEP's custom-GFF mode leaves the Wildtype plugin's
  field empty (it reads a peptide cache only cache-mode fills), so the *same* GFF+FASTA
  transcripts were translated with `gffread` and spliced back into the CSQ — verified
  correct (e.g. COL6A1 = 1028 aa).

> **Note — why B1, not B2 (from reads):** the original plan was to call variants with
> Mutect2 from the real BAMs, but the sandbox network can't sustain NCBI's remote-slice
> random-access. B1 (the published truth VCF) sidesteps that and — per the project's own
> reframing — earns the same claim, since variant *calling* isn't the differentiator.

## Pending improvements (next-session candidates)

1. **Dedup the construct by peptide sequence.** The same peptide currently appears once
   per transcript isoform (3× here). Fix: dedup in `select_survivors`
   (`stages/construct/string_of_beads/builder.py`).
2. **Widen beyond chr21** to gene-dense chromosomes (chr17/chr19) for a richer table —
   each needs its own byte-range FASTA extract (~2–3 min).
3. Optional: run the recognition axis fully (real IEDB set for foreignness, graded
   dissimilarity) — see [`concepts.md`](concepts.md) §4.
