"""
NeoantigenVaccineConstructionPipeline — concrete assembly of Stages.

Build order is back-half-first: stages 4 -> 6 -> 5 are real/native and get wired
up first; the tool-heavy front (0,1,2,3) is stubbed, then swapped for real tools
stage by stage with zero changes to this file or to core.

Run:  python -m NeoantigenVaccineConstructionPipeline.pipeline
"""
from __future__ import annotations

# --- import the shared spine from the parent dir --------------------------
# Real fix is an editable-installed package (see README / core notes); this
# bootstrap keeps us moving until then.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import Pipeline  # noqa: E402


def build_pipeline(case) -> Pipeline:
    """Assemble the full DAG for one Case. add() order is irrelevant — execution
    order is derived from declared I/O — so we add back-half-first on purpose."""
    from .stages.acquire.acquire_stage import AcquireStage
    from .stages.input.input_stage import InputStage
    from .stages.variants.variant_call_stage import VariantCallStage
    from .stages.hla.hla_type_stage import HlaTypeStage
    from .stages.candidates.candidate_stage import CandidateStage
    from .stages.rank.rank_stage import RankStage
    from .stages.eval.eval_stage import EvalStage
    from .stages.construct.construct_stage import ConstructStage

    p = Pipeline(name="neo-vaccine")
    for stage_cls in (
        RankStage, EvalStage, ConstructStage,          # back half (native) — built first
        AcquireStage, InputStage, VariantCallStage, HlaTypeStage, CandidateStage,  # front
    ):
        p.add(stage_cls(case))
    return p


if __name__ == "__main__":
    print("Usage:")
    print("  from NeoantigenVaccineConstructionPipeline.pipeline import build_pipeline")
    print("  build_pipeline(case).validate()  # dry preflight (no run)")
    print("  build_pipeline(case).run()       # execute")
