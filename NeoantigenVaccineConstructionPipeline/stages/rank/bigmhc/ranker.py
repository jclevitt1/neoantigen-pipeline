"""
BigMHcImRanker — OPTIONAL high-accuracy Axis-2 backend (non-commercial).

BigMHC_IM (Karchin lab, Nat Mach Intell 2023) is the transfer-learning
immunogenicity model with the highest reported precision on true immunogenic
neoepitopes. It is NOT the default because:
  - it is a ~5 GB git clone, not pip-installable (no PyPI package);
  - its licence is academic / non-commercial (do NOT ship in a commercial build);
  - it benefits from a GPU.

So it sits behind the same `Ranker` seam as a swap-in for teams that have cloned
BigMHC and accept those terms. Wire it with:
    RankStage(case, ranker=BigMHcImRanker(bigmhc_dir="/path/to/bigmhc"))

Following the repo convention (cf. the logistic filler and its missing pickle),
this NEVER fabricates a score: if the BigMHC checkout isn't present it raises a
clear, actionable error rather than guessing.
"""
from __future__ import annotations

import os
from pathlib import Path

from ..base import Ranker


class BigMHcImRanker(Ranker):
    """Adapter for BigMHC-IM, a transfer-learned immunogenicity predictor. Not
    implemented - declared so the seam documents the intended comparison rather than
    hiding it in a TODO."""
    name = "bigmhc-im"
    description = ("Optional: BigMHC_IM transfer-learning immunogenicity (academic "
                   "licence, ~5 GB clone, GPU-friendly). Highest reported precision.")

    def __init__(self, bigmhc_dir: str | os.PathLike | None = None):
        self.bigmhc_dir = Path(bigmhc_dir) if bigmhc_dir else None

    def _resolve(self) -> Path:
        d = self.bigmhc_dir or os.environ.get("BIGMHC_DIR")
        if not d:
            raise FileNotFoundError(
                "BigMHcImRanker needs the BigMHC checkout. Clone it "
                "(https://github.com/KarchinLab/bigmhc), then pass "
                "BigMHcImRanker(bigmhc_dir=...) or set $BIGMHC_DIR. It is a ~5 GB, "
                "academic-licence, non-commercial dependency — hence optional, not "
                "the default."
            )
        d = Path(d)
        if not (d / "src").exists():
            raise FileNotFoundError(f"no BigMHC checkout at {d} (expected a src/ dir).")
        return d

    def score(self, rows: list[dict], alleles: list[str]) -> list[dict]:
        bigmhc = self._resolve()
        # BigMHC ships a CLI (src/predict.py) that reads a peptide/allele CSV and
        # writes an immunogenicity column. Rather than reimplement its model here,
        # a production wiring shells out to that CLI and joins the result back.
        # Left as an explicit integration point so we never emit an untested score.
        raise NotImplementedError(
            f"BigMHC checkout found at {bigmhc}, but the CLI adapter is not wired "
            "in this build. Implement the src/predict.py subprocess call + column "
            "join here, or use the default LukszaCompositeRanker. See README.md."
        )
