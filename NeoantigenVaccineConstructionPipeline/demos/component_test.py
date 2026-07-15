"""
component_test.py — Option A: the stage 3->6 COMPONENT TEST assembly.

Runs the scientifically interesting back half of the pipeline
    candidate windows -> MHCflurry presentation gate -> Luksza recognition composite
    -> string-of-beads construct
on a curated panel of REAL oncogenic hotspot mutations (stages/variants/fixture/
curated.py), in ISOLATION from the genomics front end (no acquire / align / call).
This is the cheap, low-risk liveness proof; the full-tumour integration test is
Option B. See docs/e2e_validation_notes.md.

HOW THE ISOLATION WORKS
    - Stage 2a uses FixtureVariants(curated records) -> declares NO inputs, so it is a
      DAG root: the annotated VCF appears without any BAM.
    - Stage 2b uses KnownGenotypeTyper carrying a common HLA panel -> also no reads.
    - We assemble ONLY the six stages those inputs actually feed (2a,2b,3,4,5,6),
      deliberately omitting Acquire / Input / the real Mutect2 caller. Pipeline.run()
      executes every stage added, so adding those would demand BAMs -- we don't add them.
    - The one external file the minimal DAG needs is `case.proteome` (stage 5 / the
      Luksza dissimilarity-to-self term); validate() requires it to exist.

COLAB USAGE
    import sys; sys.path.insert(0, "/content/neoantigen_pipeline")  # repo root (has core.py)
    !pip -q install mhcflurry && mhcflurry-downloads fetch models_class1_presentation
    # a real human proteome for the dissimilarity term (Swiss-Prot human is small):
    !wget -qO /content/human.fasta.gz "https://rest.uniprot.org/uniprotkb/stream?format=fasta&query=organism_id:9606+AND+reviewed:true" && gunzip -f /content/human.fasta.gz
    from NeoantigenVaccineConstructionPipeline.demos.component_test import run_component_test
    out = run_component_test(workdir="/content/run_A", proteome="/content/human.fasta")
    print(out["ranked_tsv"].read_text())
"""
from __future__ import annotations

from pathlib import Path

from core import Pipeline
from ..case import Case
from ..stages.variants.variant_call_stage import VariantCallStage
from ..stages.variants.fixture.source import FixtureVariants
from ..stages.variants.fixture.curated import build_curated_records, DEMO_HLA_PANEL
from ..stages.hla.hla_type_stage import HlaTypeStage
from ..stages.hla.known.typer import KnownGenotypeTyper
from ..stages.candidates.candidate_stage import CandidateStage
from ..stages.rank.rank_stage import RankStage
from ..stages.eval.eval_stage import EvalStage
from ..stages.construct.construct_stage import ConstructStage

SAMPLE_ID = "CURATED-DEMO"


def make_case(workdir, proteome) -> Case:
    """A Case for the component test. Only `proteome` must be a real file; the
    DNA/RNA/reference roots are unused (no acquire/align/call stage is assembled),
    so they point at a placeholder path under workdir."""
    workdir = Path(workdir)
    placeholder = workdir / "_unused"
    return Case(
        sample_id=SAMPLE_ID, workdir=workdir,
        tumor_dna=placeholder, normal_dna=placeholder, tumor_rna=placeholder,
        reference=placeholder, proteome=Path(proteome),
    )


def build_component_pipeline(case, records=None) -> Pipeline:
    """Assemble ONLY stages 2a,2b,3,4,5,6 with curated inputs. No front end."""
    recs = records if records is not None else build_curated_records()
    p = Pipeline(name="curated-component-test")
    p.add(VariantCallStage(case, source=FixtureVariants(recs)))
    p.add(HlaTypeStage(case, typer=KnownGenotypeTyper(table={case.sample_id: list(DEMO_HLA_PANEL)})))
    p.add(CandidateStage(case))
    p.add(RankStage(case))          # default ranker = LukszaCompositeRanker
    p.add(EvalStage(case))
    p.add(ConstructStage(case))
    return p


def run_component_test(workdir, proteome, force: bool = True, run_self_tests: bool = True) -> dict:
    """Build the Case + minimal pipeline, (optionally) run stage self-tests, execute.

    Returns a dict of the key output Paths. Requires mhcflurry installed + models
    fetched, and `proteome` to be a real FASTA on disk.
    """
    case = make_case(workdir, proteome)
    p = build_component_pipeline(case)
    print("Plan:", " -> ".join(p.topological_order()))
    if run_self_tests:
        p.test()
    p.validate()   # preflight: DAG builds, proteome exists
    p.run(force=force)
    return {
        "candidates_tsv": case.candidates_tsv,
        "ranked_tsv": case.ranked_tsv,
        "filtered_tsv": case.filtered_tsv,
        "construct_fasta": case.construct_fasta,
        "construct_json": case.construct_json,
    }
