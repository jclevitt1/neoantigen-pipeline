# E2E Validation Plan — notes for the cold-email push

_Working notes (2026-07-14). Goal: convert the pipeline from "designed / unit-tested"
to "demonstrably runs on real data" before cold-emailing Columbia labs (Azizi + Han
first). Two complementary runs, done **separately**._

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

## OPEN DECISION — B1 vs B2 (deferred by user; pick before starting B)

| | **B1 — real VCF, skip calling** | **B2 — from real reads** |
|---|---|---|
| Input | SEQC2 published HCC1395 somatic **truth-set VCF** (NCBI SEQC2 ftp) | `Seqc2SliceSource` → real reads (chr21) |
| Toolchain to stand up | **VEP + Wildtype only** | **GATK Mutect2 *and* VEP+Wildtype**; must wire the deferred `produce()` |
| Honest claim earned | "ranked a real tumour's real somatic mutation set, end-to-end" | "*called* and ranked somatic variants from real HCC1395 reads" |
| Cost / risk | ~2 days, medium | ~3–4 days, higher |

**Recommendation: B1.** Variant *calling* (Mutect2) is the least scientifically
interesting and most plumbing-heavy step; the published truth-set VCF still earns the
"real tumour, end-to-end, no cherry-picking" claim. **B2 = stretch / "from reads" flex.**

## Caveat for BOTH runs (state honestly, don't fix)

RNA isn't remote-sliceable (needs a STAR alignment), so **expression (TPM) runs in
placeholder mode** → `LukszaCompositeRanker`'s expression gate treats unknown TPM as
"survives" (permissive). Say so in the output; don't imply real-expression filtering.

## HCC1395 inputs needed for B

- Somatic VCF (B1) or BAM slice (B2) — SEQC2 (`ReferenceSamples/seqc/Somatic_Mutation_WG`).
- HCC1395 HLA — already in repo (`KNOWN_GENOTYPES["HCC1395"]`).
- GRCh38 reference + VEP cache + Wildtype plugin.
