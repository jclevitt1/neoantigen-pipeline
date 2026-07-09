"""
LogisticTmeRanker — the FIRST ranker, and honestly a FILLER.

Wraps Model B from ../../../immunogenerative_logistic_abtest: an L1-logistic model
over 31 peptide features + a 22-dim TCGA CIBERSORTx TME proxy. Its one defensible
claim is that TME context adds a *statistically significant* signal beyond peptide
biochemistry (DeLong p<0.001 on TESLA) — but absolute AUC is modest (~0.68 TESLA,
~0.57 HiTIDE). NOT clinical-grade. It holds the stage-4 slot until a stronger
ranker replaces it; that swap is a one-liner because of the Ranker interface. See
README.md in this directory.

Design: FIT ONCE, SCORE MANY. Training reads a 715 MB table and is slow, so we
don't retrain inside the pipeline. A separate fit step pickles a bundle
(model + quantile transformer + feature list + per-feature medians); `score()`
just loads it and predicts. Missing features in a candidate row fall back to the
training median, mirroring Model B's own imputation.
"""
from __future__ import annotations

from pathlib import Path

from ..base import Ranker

# Default location of the pre-fit bundle (produced by the fit step).
_DEFAULT_MODEL = Path(__file__).with_name("logistic_tme_model.pkl")


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class LogisticTmeRanker(Ranker):
    name = "logistic-tme"
    description = "Model B: peptide + TME-proxy logistic immunogenicity. FILLER — modest AUC (~0.68), swap later."

    def __init__(self, model_path: Path | None = None):
        self.model_path = Path(model_path) if model_path else _DEFAULT_MODEL
        self._bundle = None  # lazy — loaded on first score()

    def _load(self):
        if self._bundle is not None:
            return self._bundle
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"no pre-fit model at {self.model_path}. Fit it once with the "
                "fit step (fit_logistic_tme.py) before ranking — training reads "
                "the 715 MB Neopep table and is too slow to run per-pipeline."
            )
        import pickle
        with open(self.model_path, "rb") as fh:
            self._bundle = pickle.load(fh)
        return self._bundle

    def score(self, rows: list[dict], alleles: list[str]) -> list[dict]:
        bundle = self._load()
        model = bundle["model"]
        qt = bundle["quantile_transformer"]
        features = bundle["features"]     # ordered feature names the model expects
        medians = bundle["medians"]       # {feature: training median} for imputation

        # Build the feature matrix: one row per candidate, features in order,
        # missing/non-numeric values imputed with the training median.
        X = []
        for r in rows:
            X.append([
                (_to_float(r.get(f)) if _to_float(r.get(f)) is not None else medians[f])
                for f in features
            ])

        probs = model.predict_proba(qt.transform(X))[:, 1]

        scored = []
        for r, p in zip(rows, probs):
            out = dict(r)  # never mutate the caller's row
            # binding rank the model consumed, surfaced for downstream/eval
            out["binding_affinity"] = r.get("mutant_rank_netMHCpan", r.get("binding_affinity", ""))
            out["immunogenicity"] = round(float(p), 6)
            scored.append(out)

        scored.sort(key=lambda x: x["immunogenicity"], reverse=True)
        return scored
