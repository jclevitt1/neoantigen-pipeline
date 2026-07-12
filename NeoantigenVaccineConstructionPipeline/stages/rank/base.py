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
    name: str = "unnamed-ranker"
    description: str = ""

    # Columns every ranker appends to each candidate row.
    # `immunogenicity` is the sort key (best-first); `binding_affinity` carries
    # the upstream MHC-binding rank the model consumed (netMHCpan/PRIME).
    SCORE_COLUMNS = ["binding_affinity", "immunogenicity"]

    @abstractmethod
    def score(self, rows: list[dict], alleles: list[str]) -> list[dict]:
        """rows: candidate peptides, each a dict with at least 'peptide' (plus
        whatever feature columns stage 3 produced). alleles: HLA-I calls, e.g.
        ['HLA-A*02:01', 'HLA-B*07:02', ...].

        Return the same rows widened with SCORE_COLUMNS, sorted best-first by
        immunogenicity. Must not mutate the input rows.
        """
        raise NotImplementedError
