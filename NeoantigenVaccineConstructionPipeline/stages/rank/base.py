"""
Ranker — the strategy plugged into stage 4.

Stage 4 is the one stage we expect to have many interchangeable implementations
(the whole immunogenerative_logistic_abtest is a bake-off). So the scoring logic
lives behind this interface, and `RankStage` just picks one.

A Ranker is PURE OVER DATA: it takes plain rows + the patient's alleles and
returns scored rows. The Stage owns all file I/O. That split means every ranker
is unit-testable with a hand-written fixture, and swapping one for another never
touches the Stage, the pipeline, or core.
"""
from __future__ import annotations

from abc import abstractmethod

from core import Strategy


class Ranker(Strategy):
    """Seam: how candidate peptides are scored and ordered. The most consequential
    choice in the pipeline and the one most worth swapping - implementations range
    from a bare presentation score to learned immunogenicity models."""
    name: str = "unnamed-ranker"
    description: str = ""

    # The STABLE contract columns every ranker appends. `immunogenicity` is the
    # best-first sort key; `binding_affinity` carries the MHC-binding number the
    # model consumed/produced (nM). Rankers may emit any number of EXTRA feature
    # columns beyond these (e.g. presentation_score, agretopicity,
    # dissimilarity_to_self, tier) — the Stage passes extras straight through, so
    # widening a ranker's output never touches the contract or downstream stages.
    SCORE_COLUMNS = ["binding_affinity", "immunogenicity"]

    def configure(self, case) -> None:
        """Optional hook: hand the ranker the Case before scoring, so a ranker
        that needs a file (e.g. the composite ranker loads `case.proteome` for
        dissimilarity-to-self) can load it once. Pairs with `required_inputs`,
        which declares that file as a DAG edge. Default: no-op."""

    @abstractmethod
    def score(self, rows: list[dict], alleles: list[str]) -> list[dict]:
        """rows: candidate peptides, each a dict with at least 'peptide' (plus
        whatever feature columns stage 3 produced, e.g. 'wt_peptide', 'tpm').
        alleles: HLA-I calls, e.g. ['HLA-A*02:01', 'HLA-B*07:02', ...].

        Return the same rows widened with SCORE_COLUMNS (plus any extra feature
        columns), sorted best-first by immunogenicity. Must not mutate the input
        rows.
        """
        raise NotImplementedError
