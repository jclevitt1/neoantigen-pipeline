# End-to-end validation plan

_Working notes (2026-07-14). Goal: convert the pipeline from "designed / unit-tested"
to "demonstrably runs on real data". Two complementary runs, done **separately**._

## The two runs

- **Option A — component test (stages 3→6).** Curated real oncogenic hotspot
  mutations → windows → MHCflurry presentation gate → Łuksza composite → construct.
  Proves the **ranking science** runs on real mutations. Cheap, low-risk, no genomics.
  - Entry point: `VariantCallStage(case, source=FixtureVariants(build_curated_records()))`
    — see `stages/variants/fixture/curated.py`.
  - Honest claim earned: _"runs the ranking on real mutations"_ — **not** "on a real
    tumour's genotype" (the variants are hand-picked, not called from one genome).
  - HLA: `KnownGenotypeTyper(table={sample_id: DEMO_HLA_PANEL})`.

- **Option B — integration test (VCF → 6) on HCC1395.** One real tumour's real
  somatic mutations, end-to-end. Removes the "you cherry-picked winners" objection.
  More plumbing. HLA is free — `KNOWN_GENOTYPES["HCC1395"]` is already in the repo.

**Why separately / A first:** clean fault isolation. Once A is green, stages 3→6 are
known-good, so any B breakage is unambiguously in the VCF front-end.

## What the repo already provides (verified 2026-07-14)

- Stage 2a `VariantSource` seam: `FixtureVariants` (tool-free, takes a records list,
  runs today) vs `Mutect2VepCaller` (real; `produce()` **intentionally raises** — it's
  a `COMMAND_PLAN` to transcribe in Colab).
- Stage 0 `Seqc2SliceSource`: remote region-slice (default `chr21`) of the real
  HCC1395/HCC1395BL SEQC2 BAMs — no full download; verified NCBI URLs baked in.
- Stage 2b `KnownGenotypeTyper` (`stages/hla/known/`): published cell-line HLA,
  no reads. **HCC1395 = A\*29:02, B\*08:01, B\*45:01, C\*06:02, C\*07:01** (already present).
- Stage 3 **requires `WildtypeProtein` in the VCF CSQ**.

## The one cost center for B: VEP + Wildtype plugin

Stage 3 needs `WildtypeProtein` in the CSQ, produced **only** by `vep --plugin Wildtype`
(the pVACseq trick). So *any* B flavour must stand up VEP + the ~15 GB GRCh38 cache +
the Wildtype plugin in Colab. That is the main risk / time sink. Confirm contig naming
(`chr21` vs `21`) once with `samtools view -H`.

## DECISION — full B2 (from real reads), chr21 slice, one notebook (chosen 2026-07-15)

**Chosen: run the WHOLE front-end from real reads** — acquire → (sort/index) → Mutect2
call → VEP+Wildtype annotate → stages 3→6. Validates the full pipeline, not a slice of
stage 2. Rejected B1 (skip-calling) because the point is to prove the front-end, and
`Mutect2` is cheap here (pre-aligned BAMs, matched normal). One notebook, two clearly
marked halves; the "subset" is the built-in **chr21 read-slice**, not a VCF subset.

**Framing:** Option A already validated stages 3→6 (vaccine construction).
Option B is really **"test stage 2 in isolation"** (the genomics front-end) as a single
gate, **then** run construction after — all in one notebook, with a marker where the
stage-2 test ends.

### Stage map for the run
| stage | how it runs | tooling |
|---|---|---|
| 0 acquire | **executes** (`Seqc2SliceSource.ensure`) | `samtools view <url> chr21` on real SEQC2 tumor+normal BAMs |
| 1 input | pre-aligned BAM → **sort+index only** (no aligner) | `samtools` — verified in `input_stage.py` (`["sort","index"]`) |
| 2a variants | **transcribe `COMMAND_PLAN`** (stage raises by design) | GATK Mutect2 → FilterMutectCalls → `vep --plugin Wildtype` |
| 2b HLA | executes, free | `KnownGenotypeTyper` (HCC1395 genotype in repo) |
| 3→6 | executes (Option-A-validated) | MHCflurry + native — a `demos/integration_test.py` |

### Two facts that de-risk it (from reading the code 2026-07-15)
- **No alignment step.** SEQC2 BAMs are already BWA-MEM aligned+indexed; a region-slice
  of a sorted BAM stays sorted → stage 1 is sort+index, NOT bwa/STAR. Big toolchain cut.
- **Transcription, not `produce()`.** Stages 1 and 2a deliberately raise
  `NotImplementedError` **with a command plan** (design intent: "the Colab run is a
  transcription, not a redesign"). So Part 1 transcribes the real Mutect2+VEP commands
  into cells; we do NOT implement `produce()` as subprocess (untestable locally, against
  the grain).

### The real cost / risk (all in Part 1 setup)
- **VEP + Wildtype plugin + ~15 GB GRCh38 cache** in Colab — the dominant fixed cost.
- **GATK** install + a GRCh38 reference (`.fai`+`.dict`) for chr21.
- **Contig naming** must agree across BAM / reference / VEP cache (`chr21` vs `21`).
  Confirm FIRST: `samtools view -H <url> | grep @SQ | head`. Classic footgun.
- Expect 2–3 Colab debug iterations (paths, contigs, cache flags). ~3–4 days.

### Honest caveats to print in the output
DNA-only (no RNA slice) → expression permissive; chr21-only → a real *slice* of the
tumour, stated plainly (not the whole genome).

## Parked for later (extensions, not needed for the current milestone)

- **Full genome-wide run (drop the chr21 slice).** Once the VEP+GATK toolchain is
  reliably stood up in Colab (the hard part), widen `region` beyond chr21 for the full
  HCC1395 mutation count / a bigger ranked table. Pure scale-up of a known-good path.
- **RNA / real expression.** SEQC2 tumor RNA is raw FASTQ (needs a STAR alignment), so
  it's a separate follow-up; until then expression tagging (stage 3) stays permissive.
- **B1 (skip-calling from the SEQC2 truth-set VCF)** remains a cheaper fallback if the
  Mutect2 setup proves too costly in Colab — annotate the published truth VCF with
  VEP+Wildtype and enter at stage 3. Not the plan, but the escape hatch.

## Caveat for BOTH runs (state honestly, don't fix)

RNA isn't remote-sliceable (needs a STAR alignment), so **expression (TPM) runs in
placeholder mode** → `LukszaCompositeRanker`'s expression gate treats unknown TPM as
"survives" (permissive). Say so in the output; don't imply real-expression filtering.

## HCC1395 inputs needed for B

- Somatic VCF (B1) or BAM slice (B2) — SEQC2 (`ReferenceSamples/seqc/Somatic_Mutation_WG`).
- HCC1395 HLA — already in repo (`KNOWN_GENOTYPES["HCC1395"]`).
- GRCh38 reference + VEP cache + Wildtype plugin.
