# CLAUDE.md — neoantigen_pipeline

End-to-end replication of a personalized cancer-vaccine **design** pipeline
(matched tumor/normal sequencing → neoantigen ranking → vaccine construct). Wraps
the existing Model A/B ranker (`../immunogenerative_logistic_abtest`) as stage 4.

**Scope boundary (state it honestly):** designs a construct in silico; does NOT
validate efficacy — that needs wet-lab assays (ELISpot/tetramer) or animal models.
The pipeline stops exactly where silicon hands off to the lab.

## Architecture (locked)

- **One abstraction: `Stage`** (`core.py`) — a typed-file transform. Declares
  `inputs`/`outputs` (list[Path]), a `run()`, and skips itself if outputs are
  fresher than inputs (mtime cache). Optional hooks: `dry_check_inputs/outputs`
  (cheap format validation), `self_test`, plus `kind` / `description` metadata.
- **`Pipeline`** (`core.py`) — a set of Stages with `.run()`. Execution order is
  **derived from declared I/O** (topological sort; `add()` order only breaks
  ties). It's a DAG, NOT a linear state machine. `.validate()` preflights the
  graph (cycles, duplicate producers, missing external inputs) without running;
  `.to_graph()` emits structure for visualization.
- **`Case`** (`NeoantigenVaccineConstructionPipeline/case.py`) — one patient's
  raw inputs + typed derived paths. Swap HCC1395 → COLO829 = one Case.
- **Two flavors of Stage:** *adapters* (0-acquire, 1, 2a, 2b, 3 — wrap tools like
  samtools, Mutect2, VEP, OptiType, pVACseq) vs *native* (4-rank, 6-eval,
  5-construct — our code). Tests differ: native get hard fixture assertions;
  adapters get contract/smoke checks.
- **Stages are packages** (`stages/<stage>/<stage>_stage.py` + `<approach>/`
  subdirs), each with its own READMEs — see the "Stages layout" section.
- **`viz.py`** — domain-agnostic; renders any Pipeline to a standalone HTML DAG
  view (`pipeline_view.html`), AWS-style cards, dashed-amber skip-edges.
- Parallelism (concurrent executor for the one 2a‖2b pair) deliberately DEFERRED
  — DAG is explicit, so it's a drop-in later that touches no Stage. Not worth it
  now (only one parallel pair, tools already internally multithreaded).

## DAG (derived order)

    0-acquire → 1-input → 2a-variants → 2b-hla → 3-candidates → 4-rank → 6-eval → 5-construct

The peptide TSV is one table traveling 3→4→6, gaining columns. `6 gates 5`
(filter, then build survivors). Skip-edges: `2b-hla→4-rank` (hla.json),
`1-input→3-candidates` (tumor_rna.bam).

## Status

- [x] `core.py` spine — Stage + Pipeline + topo-sort + dry-check hooks + validate + to_graph
- [x] `Case`, `checks.py` (cheap validators)
- [x] All 7 stage **contracts** — I/O + dry checks + description; `run()` stubs raise NotImplementedError
- [x] `viz.py` + `pipeline_view.html` (read-only DAG view)
- [~] **Stage logic** — back-half-first:
  - [x] **4-rank** — `RankStage` owns I/O, delegates to a pluggable `Ranker`
    (`stages/rank/logistic_tme/`); default `LogisticTmeRanker` (documented filler).
    Only the fit-pickle step remains before it scores live. **MVP-working.**
  - [x] **6-eval** — three filters (autoimmunity = exact proteome match;
    clonality = CCF≥0.9; manufacturability = GRAVY + cysteine rules). Flags,
    doesn't drop. Native `self_test` passes on build. **Done.**
  - [x] **5-construct** — string-of-beads: survivor gate → AAY-linked polypeptide
    → codon-optimized nucleotide ORF → construct.fasta (AA+NT) + construct.json
    recipe. `self_test` passes; MVP omissions recorded in the recipe. **Done.**
  - **Back half now runs end-to-end from a fixture** (ranked.tsv → eval → construct).
  - [x] **0-acquire** — stage data (pluggable `AcquireSource`): `on_disk`
    (default, verify present) + `seqc2_slice` (region-slice remote SEQC2 BAMs via
    `samtools view <url> <region>`, no full download). Contract + DAG wired; **DNA
    URLs verified** (see Data below). `seqc2_wes_dna_manifest()` builds them.
    **Done.**
  - [ ] Front-half *starters* (2b-hla → 2a-variants/3-candidates on a
    single-chromosome HCC1395 subset → 1-input) + the `fit_logistic_tme.py`
    pickle so stage 4 scores live. Front half only needs real-shaped files.
    RNA/expression deferred: tumor RNA is FASTQ → needs a STAR align first (see Data).
- [ ] MVP target: one Case end-to-end → ranked+filtered peptides + construct FASTA (back half real, front stubbed/subset)

## Cloud (Google Colab)
Disk-cheap, download-nothing-locally. Data lives in the cloud; `seqc2_slice` pulls
one region (chr21 ≈ 100s MB) into ephemeral Colab scratch. Code in git (KB), tiny
shared refs (proteome, model pickle) on Google Drive. See `cloud/README.md` for the
bootstrap cells. Colab free = $0; graduates unchanged to a spot VM + GCS bucket.

**Case path convention:** raw sample files (`tumor_dna`…) must live in a `raw/`
subdir, distinct from the normalized `*_bam` paths in `workdir` — else `0-acquire`
and `1-input` would declare the same output and the DAG rejects it.

## Stages layout (documentation convention)
Each stage is a package `stages/<stage>/` with:
- `README.md` — general concept/biology + the I/O contract (read this to relearn
  the stage);
- `<stage>_stage.py` — the `Stage` subclass (contract + orchestration);
- `<approach>/` subdir(s) — a specific tool/method, with its own `README.md` and
  implementation. General biology lives at the stage level; approach specifics nest
  under it. `rank/` shows the pattern fully (pluggable `Ranker` + `logistic_tme/`).

## TODO / backlog (running)
1. **Replace the stage-4 ranker.** `LogisticTmeRanker` (Model B) is a documented
   *filler* — modest AUC (~0.68 TESLA, ~0.57 HiTIDE), not clinical-grade. Swap for
   a stronger peptide-immunogenicity predictor. **Prereq (deferred, not started):**
   a literature search on the best predictors of peptide immunoresponsiveness.
   Drop-in via the `Ranker` interface — no Stage/pipeline changes.
   - Ref: `../immunogenerative_logistic_abtest/RESULTS.md` — Model A/B/C
     benchmarks, TESLA/HiTIDE, DeLong significance on the TME thesis.

## Deferred / later
- Package `core`+`viz` as an editable-installable `pipekit` (solves cross-project
  imports; removes the `sys.path` bootstrap in `pipeline.py`).
- Publish `pipeline_view.html` as a shareable hosted link.
- Concurrent executor once 2a/2b exist and the wait is felt.

## Docs
- `docs/safety_testing.md` — safety-testing notes + resources: the 2013 titin
  cardiotoxicity case (Linette/Cameron), the cell-*state* lesson behind why it
  slipped preclinical screens, what the wet lab does/doesn't cover, and the human
  neoantigen-vaccine success record. Context for the stage-6 autoimmunity filter.

## Data (public, no approval to start)
HCC1395/HCC1395BL (breast, SEQC2 benchmark) + COLO829/COLO829BL (melanoma) = two
matched tumor/normal pairs. TCGA open-tier MAFs for downstream breadth. Controlled
dbGaP BAMs are routed around, not required.

### Verified SEQC2 locations (browsed 2026-07)
- **DNA WES BAMs (tumor+normal), indexed** — remote-sliceable. Base:
  `https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/seqc/Somatic_Mutation_WG/data/WES`
  pattern `WES_<CENTER>_<T|N>_<rep>.bwa.dedup.bam` (+ `.bai`); centers EA/FD/IL/LL/NC/NV.
  Demo pair: `WES_EA_T_1` / `WES_EA_N_1`. `.bai` co-located (SEQC-II_bai.md5 present).
- **Tumor RNA — separate follow-up.** Not in the somatic FTP tree; it's raw FASTQ
  under SRA `SRX8401273–5` (BioProject `PRJNA635123`) → needs STAR alignment before
  it's a sliceable BAM. RNA/expression (stage 3) is a starter until then.
- **Confirm at pull time:** contig naming (`chr21` vs `21`) via
  `samtools view -H <url> | grep '@SQ' | head`; set `region` to match.
- Project: SRA `SRP162370`.

## Run
    # from neoantigen_pipeline/
    python -m NeoantigenVaccineConstructionPipeline.pipeline        # usage
    # build_pipeline(case).validate()  → dry preflight
    # build_pipeline(case).run()       → execute (stubs raise until logic lands)
    open NeoantigenVaccineConstructionPipeline/pipeline_view.html   # DAG view

## Security (before any publish)
`.gitignore` already blocks `.env`, secrets, and all big/derived data (BAM/VCF/
FASTA/reference). Keep it that way. The sibling `regen_rag`/Corpus project holds
a live ANTHROPIC_API_KEY in its own `.env` — never commit that.
