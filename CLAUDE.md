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
- **Two flavors of Stage:** *native* (our own logic — 3-candidates, 4-rank,
  6-eval, 5-construct, plus the default typer/expression paths) vs *adapters*
  (wrap external tools — 1-input, 2a-variants, and the OptiType/pVACseq paths).
  Several stages are hybrids via a **pluggable seam** (`Ranker`, `AcquireSource`,
  `HlaTyper`, `ExpressionSource`, `VariantSource`): a native default that runs
  today + a tool-backed option that declares its own inputs. Native logic (incl.
  the tool-output *parsers*, and 2a's VCF *writer*) gets hard fixture assertions
  in `self_test`; only the tool *execution* defers to Colab. Exception: 2a's
  *default* is the tool adapter, because somatic calling can't be faked from
  nothing — the native `fixture` source is opt-in for wiring runs.
- **Stages are packages** (`stages/<stage>/<stage>_stage.py` + `<approach>/`
  subdirs), each with its own READMEs — see the "Stages layout" section.
- **`Strategy`** (`core.py`) — marker base for the pluggable seam. Every seam ABC
  (`Ranker`, `AcquireSource`, `HlaTyper`, `ExpressionSource`, `VariantSource`)
  inherits it, which makes "which impl is active + what the alternatives are" a
  first-class, introspectable fact. `Pipeline.to_graph()` auto-derives it — no
  per-stage wiring — so the diagram documents the seam for free.
- **`viz.py`** — domain-agnostic; renders any Pipeline to a standalone **interactive**
  HTML view (`pipeline_view.html`): click a stage → drawer auto-populated from the
  abstraction (active strategy + alternatives w/ docstrings, live `self_test` dot,
  IN/OUT, up/down-stream, the stage's class docstring + README.md rendered).
  Hover traces dependencies; native/adapter filter. Everything is derived from
  `to_graph()`, so adding a stage or swapping a strategy updates the view with no
  edits to viz. Regenerate: `viz.write_html(build_pipeline(case), "…/pipeline_view.html")`.
- Parallelism (concurrent executor for the one 2a‖2b pair) deliberately DEFERRED
  — DAG is explicit, so it's a drop-in later that touches no Stage. Not worth it
  now (only one parallel pair, tools already internally multithreaded).

## DAG (derived order)

    0-acquire → 1-input → 2a-variants → 2b-hla → 3-candidates → 4-rank → 6-eval → 5-construct

The peptide TSV is one table traveling 3→4→6, gaining columns. `6 gates 5`
(filter, then build survivors). Skip-edges: `2b-hla→4-rank` (hla.json),
`1-input→3-candidates` (tumor_rna.bam).

## Status

- [x] `core.py` spine — Stage + Pipeline + `Strategy` seam + topo-sort + dry-check
  hooks + validate + `to_graph` (auto-derives active strategy/alternatives) +
  `Stage.test_status()` (precise pass/fail/no-test; fixed the old inverted `test()`)
- [x] `Case`, `checks.py` (cheap validators)
- [x] All 7 stage **contracts** — I/O + dry checks + description; `run()` stubs raise NotImplementedError
- [x] `viz.py` + `pipeline_view.html` — **interactive**, self-documenting view
  (click→drawer: strategy+alternatives, live self_test, README/docstring; hover-trace)
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
  - [x] **3-candidates** — NATIVE window generator (`stages/candidates/native/`):
    pure `windows.py` (mutant protein → covering 8–11mers), `vcf.py` (VEP-CSQ
    reader, no pysam), pluggable `ExpressionSource` (default `PlaceholderExpression`
    → `tpm=NA`, needs no RNA so it runs today; `FeatureCountsExpression` stub
    declares the RNA BAM input for later). Hard `self_test` on a KRAS-G12D fixture
    VCF passes; `execute()` writes candidates.tsv. Handles missense; frameshift is
    a documented extension. **Done (MVP).**
  - [x] **2b-hla** — pluggable `HlaTyper` (`stages/hla/`): default
    `KnownGenotypeTyper` (published HCC1395/COLO829 genotypes, sourced from
    Cellosaurus/TCLP PMID 26589293 — zero inputs, runs today) + `OptiTypeTyper`
    with a real, tested `parse_optitype_tsv` (tool run deferred). Output validated
    against class-I nomenclature (`HLA-[ABC]*NN:NN`). Hard `self_test` passes;
    `execute()` writes hla.json. **Done (MVP).**
  - [x] **2a-variants** — pluggable `VariantSource` (`stages/variants/`): default
    `Mutect2VepCaller` (declares tumor+normal BAM + reference; call+VEP-annotate
    execution deferred to Colab, `COMMAND_PLAN` documented, incl. `--plugin
    Wildtype`) + native `FixtureVariants` (labelled *didactic* KRAS-G12D record on
    the real KRAS protein — not a sample measurement; zero inputs, runs today).
    The owned+tested piece is `base.write_annotated_vcf`; `self_test` round-trips
    it **through stage 3's own parser**, proving the 2a→3 CSQ hand-off is
    byte-compatible. Verified: 2a-fixture → 3 yields the same 35 candidates.
    **Done (MVP).**
  - [ ] Remaining front-half *starters*: 1-input (passthrough sort/index), + the
    `fit_logistic_tme.py` pickle so stage 4 scores live. Front half only needs
    real-shaped files. RNA/expression deferred: tumor RNA is FASTQ → needs a STAR
    align first (see Data), then swap in `FeatureCountsExpression`.
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
