"""
The demo Case used to render the documentation view.

No data needs to exist: `to_graph()` reads *declared* paths, so this Case is enough
to draw the DAG, resolve which strategy each stage is using, and run every
`self_test`. Keeping it here makes regenerating `pipeline_view.html` a one-liner
instead of an ad-hoc snippet someone has to reinvent:

    python -m NeoantigenVaccineConstructionPipeline.cases.demo

Raw inputs deliberately sit under `raw/` — stage 0 writes them and stage 1 writes the
normalized `*_bam` paths, so they must not collide or the DAG rejects the graph as
having two producers for one file.
"""
from __future__ import annotations

from pathlib import Path


def demo_case(workdir="/tmp/neo_demo_case"):
    """A representative HCC1395 Case: real SEQC2-style filenames, no real bytes."""
    from ..case import Case

    wd = Path(workdir)
    raw = wd / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    return Case(
        sample_id="HCC1395",
        workdir=wd,
        tumor_dna=raw / "SRR_tumor.bam",
        normal_dna=raw / "SRR_normal.bam",
        tumor_rna=raw / "SRX840127.fastq.gz",
        reference=raw / "GRCh38.fa",
        proteome=raw / "UP000005640.fa",
    )


if __name__ == "__main__":
    from ..pipeline import write_view

    out = Path(__file__).resolve().parent.parent / "pipeline_view.html"
    print("wrote", write_view(demo_case(), out, run_self_tests=True))
