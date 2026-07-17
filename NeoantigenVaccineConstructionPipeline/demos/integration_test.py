"""
integration_test.py — Option B: the FULL-PIPELINE integration test on a real tumour.

Where Option A (component_test.py) hand-fed curated mutations into stages 3->6, this
runs the genomics FRONT END on a real tumour (HCC1395, the SEQC2 truth pair) and then
the same validated back half:

    acquire (chr21 slice of real BAMs) -> sort/index -> Mutect2 call -> VEP+Wildtype
    annotate  ==== the STAGE-2 test ====  then  candidates -> gate -> rank -> construct

Two clearly separated halves, mirroring how the notebook is laid out (see
notebooks/option_B_integration_test.ipynb and docs/e2e_validation_notes.md):

  PART 1 - STAGE-2 TEST (front end).  Heavy external tooling (samtools / GATK Mutect2 /
     Ensembl VEP + Wildtype plugin + the ~15 GB GRCh38 cache) does NOT run through the
     pipeline object -- stages 1 and 2a intentionally raise with a command plan
     ("the Colab run is a transcription, not a redesign"). So Part 1 is transcribed
     command cells in the notebook; this module only provides:
       - make_case()          : the one Case both halves share (fixed workdir paths)
       - build_acquire()      : the Seqc2SliceSource that DOES execute (samtools slice)
       - assert_stage2_vcf()  : the single programmatic GATE closing the stage-2 test --
                                proves the front end produced a usable annotated VCF.

  PART 2 - VACCINE CONSTRUCTION (validated back half).  build_construction_pipeline()
     assembles ONLY stages 2b,3,4,5,6, reading the real case.somatic_vcf as an external
     DAG root. This is exactly the code path Option A already proved green; the only new
     thing is that its input VCF now came from real reads, not a fixture.

WHAT'S REAL vs PLACEHOLDER
  - HLA is real & free: KnownGenotypeTyper() resolves sample_id "HCC1395" from its
    published table (HLA-A*29:02, B*08:01/45:01, C*06:02/07:01; HLA-A homozygous).
  - Expression is permissive: DNA-only (no RNA slice), so stage 3 tags tpm=NA and
    nothing is dropped for low expression. State this in the writeup; don't imply
    real expression filtering.
  - chr21-only: a real *slice* of the tumour, honestly a slice -- not the whole genome.

COLAB USAGE (see the notebook for the full Part-1 command transcription)
    import sys; sys.path.insert(0, "/content/neoantigen_pipeline")
    from NeoantigenVaccineConstructionPipeline.demos import integration_test as B
    case = B.make_case("/content/run_B", proteome="/content/human.fasta",
                       reference="/content/GRCh38.chr21.fa")
    # --- Part 1 (notebook cells): B.build_acquire(case).ensure(case); Mutect2+VEP ... ---
    B.assert_stage2_vcf(case)                 # <-- stage-2 gate; raises if the VCF is bad
    # --- Part 2: run the validated construction back half ---
    out = B.run_construction("/content/run_B", proteome="/content/human.fasta")
    print(out["ranked_tsv"].read_text())
"""
from __future__ import annotations

import re
from pathlib import Path

from core import Pipeline
from ..case import Case
from ..stages.hla.hla_type_stage import HlaTypeStage
from ..stages.hla.known.typer import KnownGenotypeTyper
from ..stages.candidates.candidate_stage import CandidateStage
from ..stages.rank.rank_stage import RankStage
from ..stages.eval.eval_stage import EvalStage
from ..stages.construct.construct_stage import ConstructStage
from ..stages.acquire.seqc2_slice.source import (
    Seqc2SliceSource, seqc2_wes_dna_manifest, DEFAULT_REGION,
)

SAMPLE_ID = "HCC1395"   # resolves to the published genotype in KnownGenotypeTyper


def make_case(workdir, proteome, reference=None) -> Case:
    """The single Case both halves share. Raw-input paths are real acquire TARGETS
    (Seqc2SliceSource writes the chr21 slices there); `reference` is required for
    Part 1's Mutect2 but unused by the Part-2 construction pipeline, so it defaults
    to a placeholder for construction-only runs."""
    workdir = Path(workdir)
    ref = Path(reference) if reference is not None else (workdir / "_unused_reference")
    return Case(
        sample_id=SAMPLE_ID, workdir=workdir,
        tumor_dna=workdir / "tumor_dna.raw.bam",
        normal_dna=workdir / "normal_dna.raw.bam",
        tumor_rna=workdir / "tumor_rna.raw.bam",   # unused (DNA-only)
        reference=ref, proteome=Path(proteome),
    )


def build_acquire(center: str = "EA", region: str = DEFAULT_REGION) -> Seqc2SliceSource:
    """The stage-0 source that DOES execute in Colab: a samtools region-slice of the
    real SEQC2 WES tumor+normal BAMs (DNA-only manifest). Confirm contig naming
    (`chr21` vs `21`) against the BAM header before trusting `region`."""
    return Seqc2SliceSource(seqc2_wes_dna_manifest(center=center), region=region)


# The CSQ subfield the Wildtype plugin must inject (stage 3 parses it to build the
# WT peptide for agretopicity). Its presence is the crux of the stage-2 test.
_WILDTYPE_KEY = "WildtypeProtein"


def assert_stage2_vcf(case) -> dict:
    """The STAGE-2 GATE — the single test that closes the front-end half.

    Proves Part 1 produced a *usable* annotated somatic VCF: the file exists and is
    non-empty, its CSQ header declares the WildtypeProtein subfield, it has >=1 record,
    and at least one record actually carries a non-empty WildtypeProtein value (a
    declared-but-never-populated field would silently break stage 3's agretopicity).
    Returns a small summary dict; raises AssertionError with a specific reason on
    failure so the notebook stops at the front end rather than feeding junk downstream.
    """
    vcf_path = Path(case.somatic_vcf)
    if not vcf_path.exists() or vcf_path.stat().st_size == 0:
        raise AssertionError(
            f"stage-2 gate: {vcf_path} missing/empty — Part 1 (acquire -> Mutect2 -> "
            f"VEP+Wildtype) did not produce the annotated VCF. See the notebook's Part 1."
        )

    text = vcf_path.read_text()
    header_declares_wt = False
    csq_fields: list[str] = []       # the CSQ subfield order, read from the header
    records = 0
    records_with_wt = 0
    genes: set[str] = set()

    for line in text.splitlines():
        if line.startswith("##"):
            if line.startswith("##INFO=<ID=CSQ"):
                m = re.search(r"Format:\s*([^\">]+)", line)
                if m:
                    csq_fields = m.group(1).strip().split("|")
                if _WILDTYPE_KEY in line:
                    header_declares_wt = True
            continue
        if line.startswith("#") or not line.strip():
            continue
        records += 1
        # index CSQ subfields BY NAME (real VEP CSQ has ~26 fields in a fixed but
        # non-trivial order — WildtypeProtein is NOT last, SYMBOL is NOT first).
        wt_i = csq_fields.index(_WILDTYPE_KEY) if _WILDTYPE_KEY in csq_fields else -1
        sym_i = csq_fields.index("SYMBOL") if "SYMBOL" in csq_fields else -1
        for field in line.split("\t")[7].split(";"):
            if field.startswith("CSQ="):
                for tx in field[4:].split(","):
                    parts = tx.split("|")
                    if 0 <= sym_i < len(parts) and parts[sym_i]:
                        genes.add(parts[sym_i])
                    if 0 <= wt_i < len(parts) and parts[wt_i].strip():
                        records_with_wt += 1

    if not header_declares_wt:
        raise AssertionError(
            "stage-2 gate: CSQ header does not declare WildtypeProtein — VEP ran without "
            "`--plugin Wildtype`. Stage 3 needs it to build the WT peptide (agretopicity)."
        )
    if records == 0:
        raise AssertionError("stage-2 gate: annotated VCF has 0 variant records.")
    if records_with_wt == 0:
        raise AssertionError(
            "stage-2 gate: WildtypeProtein declared but empty on every record — the "
            "plugin is wired but not populating. Check the Wildtype plugin + --fasta."
        )

    summary = {
        "vcf": vcf_path,
        "records": records,
        "records_with_wildtype": records_with_wt,
        "genes_sample": sorted(genes)[:12],
    }
    print(
        f"stage-2 gate PASSED: {records} variants, {records_with_wt} with WildtypeProtein; "
        f"genes e.g. {summary['genes_sample']}"
    )
    return summary


def build_construction_pipeline(case) -> Pipeline:
    """PART 2: assemble ONLY stages 2b,3,4,5,6. The real annotated VCF from Part 1 is
    consumed by stage 3 as an EXTERNAL DAG root (no front-end stage is added, so the
    pipeline never tries to re-call it — the same isolation trick component_test.py
    uses for the proteome)."""
    p = Pipeline(name="hcc1395-integration-construction")
    p.add(HlaTypeStage(case, typer=KnownGenotypeTyper()))   # HCC1395 from published table
    p.add(CandidateStage(case))
    p.add(RankStage(case))          # default ranker = LukszaCompositeRanker
    p.add(EvalStage(case))
    p.add(ConstructStage(case))
    return p


def run_construction(workdir, proteome, reference=None,
                     force: bool = True, run_self_tests: bool = True) -> dict:
    """Run the Part-2 construction back half over a real annotated VCF produced by
    Part 1. Gates on assert_stage2_vcf() first, so a bad/missing front-end VCF fails
    loudly here instead of producing an empty ranked table.

    Requires: mhcflurry installed + models fetched, a real `proteome` FASTA, and
    case.somatic_vcf already written by Part 1 (see the notebook)."""
    case = make_case(workdir, proteome, reference)
    assert_stage2_vcf(case)                       # front-end gate
    p = build_construction_pipeline(case)
    print("Plan:", " -> ".join(p.topological_order()))
    if run_self_tests:
        p.test()
    p.validate()                                  # preflight: DAG builds, VCF + proteome exist
    p.run(force=force)
    return {
        "candidates_tsv": case.candidates_tsv,
        "ranked_tsv": case.ranked_tsv,
        "filtered_tsv": case.filtered_tsv,
        "construct_fasta": case.construct_fasta,
        "construct_json": case.construct_json,
    }
