"""
core.py — domain-agnostic pipeline spine.

Two abstractions, nothing else. No bio, no I/O formats — reusable anywhere.

    Stage     : a typed-file transform. Declared input files -> run() -> declared
                output files. Skips itself if its outputs are already fresh.
    Pipeline  : an ordered list of Stages with a .run(). The list is a manual
                topological order of the DAG; each Stage skips if cached, so
                re-running only redoes what actually changed.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
import time


class Stage(ABC):
    """A single typed-file transform.

    Subclass and implement three things: `inputs`, `outputs`, `run`.
    The base class handles the boring, universal parts — skip-if-cached and
    contract validation (inputs must exist before; outputs must exist after).
    """

    #: human-readable label, shown by Pipeline.run(). Override in subclass.
    name: str = "unnamed-stage"

    #: optional tag for visualization/grouping (e.g. "native" vs "adapter").
    kind: str = "stage"

    #: optional one-line description, surfaced in the HTML view.
    description: str = ""

    # --- the contract a subclass must declare -------------------------------
    @property
    @abstractmethod
    def inputs(self) -> list[Path]:
        """Files this stage reads. May be empty (e.g. a fetch stage)."""

    @property
    @abstractmethod
    def outputs(self) -> list[Path]:
        """Files this stage writes. This is the typed hand-off to the next stage."""

    @abstractmethod
    def run(self) -> None:
        """Do the work: read self.inputs, write self.outputs."""

    # --- optional per-stage test hook (auto-run by Pipeline.test) -----------
    def self_test(self) -> str | None:
        """Optional. Raise to fail; return None to signal 'no test defined'.

        Native stages override this with real assertions on a fixture.
        Adapter stages override it with a contract/smoke check.
        """
        return None

    # --- universal machinery (don't override) -------------------------------
    def is_cached(self) -> bool:
        """True if every output exists and is at least as new as every input."""
        outs = self.outputs
        if not outs or not all(p.exists() for p in outs):
            return False
        existing_inputs = [p for p in self.inputs if p.exists()]
        if not existing_inputs:  # no file inputs (e.g. fetch): cached iff outputs exist
            return True
        newest_input = max(p.stat().st_mtime for p in existing_inputs)
        oldest_output = min(p.stat().st_mtime for p in outs)
        return oldest_output >= newest_input

    def _validate_inputs(self) -> None:
        missing = [str(p) for p in self.inputs if not p.exists()]
        if missing:
            raise FileNotFoundError(f"[{self.name}] missing inputs: {missing}")

    def _validate_outputs(self) -> None:
        missing = [str(p) for p in self.outputs if not p.exists()]
        if missing:
            raise RuntimeError(f"[{self.name}] run() produced no output: {missing}")

    # --- optional dry validations (override; cheap, no heavy work) ----------
    def dry_check_inputs(self) -> None:
        """Cheap format/content checks on inputs. Raise on malformed. Override."""

    def dry_check_outputs(self) -> None:
        """Cheap format/content checks on outputs. Raise on malformed. Override."""

    def preflight(self) -> None:
        """Validate inputs exist and pass dry checks — WITHOUT running."""
        self._validate_inputs()
        self.dry_check_inputs()

    def execute(self, force: bool = False) -> str:
        """Full lifecycle. Returns 'cached' or 'ran'."""
        if not force and self.is_cached():
            return "cached"
        self._validate_inputs()
        self.dry_check_inputs()
        self.run()
        self._validate_outputs()
        self.dry_check_outputs()
        return "ran"


@dataclass
class Pipeline:
    """A set of Stages with a .run(). Domain-agnostic and reusable.

    You .add() stages in any order; execution order is *derived* from the
    declared I/O — a stage runs after whichever stage produces its inputs. The
    DAG is recovered from the data, not hand-ordered. (Execution is sequential
    for now; because the DAG is explicit, a concurrent executor is a drop-in
    upgrade that touches no Stage.)
    """

    stages: list[Stage] = field(default_factory=list)
    name: str = "pipeline"

    def add(self, stage: Stage) -> "Pipeline":
        """Register a stage. Order of add() calls only breaks ties. Chainable."""
        self.stages.append(stage)
        return self

    def _dependency_order(self) -> list[Stage]:
        """Topological sort from declared I/O. Insertion order breaks ties.

        A stage depends on the stage(s) that produce its input files. Inputs
        that no stage produces are external roots (fetched data, references) —
        not an error. Raises on duplicate producers or a dependency cycle.
        """
        producer: dict[Path, Stage] = {}
        for st in self.stages:
            for out in st.outputs:
                key = Path(out).resolve()
                if key in producer:
                    raise ValueError(
                        f"[{self.name}] two stages produce {out}: "
                        f"'{producer[key].name}' and '{st.name}'"
                    )
                producer[key] = st

        indegree: dict[Stage, int] = {st: 0 for st in self.stages}
        dependents: dict[Stage, list[Stage]] = {st: [] for st in self.stages}
        for st in self.stages:
            upstream = {
                producer[Path(inp).resolve()]
                for inp in st.inputs
                if Path(inp).resolve() in producer
                and producer[Path(inp).resolve()] is not st
            }
            indegree[st] = len(upstream)
            for up in upstream:
                dependents[up].append(st)

        order: list[Stage] = []
        remaining = list(self.stages)  # preserves insertion order
        while remaining:
            ready = [st for st in remaining if indegree[st] == 0]
            if not ready:
                raise ValueError(f"[{self.name}] dependency cycle among: "
                                 f"{[st.name for st in remaining]}")
            nxt = ready[0]  # first-added among ready -> deterministic
            remaining.remove(nxt)
            order.append(nxt)
            for dep in dependents[nxt]:
                indegree[dep] -= 1
        return order

    def topological_order(self) -> list[str]:
        """Derived execution order, as stage names. Cheap dry-run of the plan."""
        return [st.name for st in self._dependency_order()]

    def validate(self) -> list[str]:
        """Preflight without running: the DAG builds (no cycles / duplicate
        producers), and every *external* input (one no stage produces) exists on
        disk. Returns the planned order. Cheap — call before a long run."""
        order = self._dependency_order()
        produced = {Path(o).resolve() for st in self.stages for o in st.outputs}
        dangling = [
            (st.name, str(inp))
            for st in self.stages
            for inp in st.inputs
            if Path(inp).resolve() not in produced and not Path(inp).exists()
        ]
        if dangling:
            raise FileNotFoundError(f"[{self.name}] missing external inputs: {dangling}")
        return [st.name for st in order]

    def to_graph(self) -> dict:
        """Structured DAG for visualization. Nodes carry inputs/outputs (basenames,
        inputs flagged external if no stage produces them) and a layer (longest
        path from a root). Edges are producer->consumer, flagged `skip` when they
        span more than one layer (an output handed to a non-adjacent stage)."""
        order = self._dependency_order()
        producer = {Path(o).resolve(): st for st in self.stages for o in st.outputs}

        layer: dict[Stage, int] = {}
        for st in order:  # topo order => producers seen before consumers
            preds = [producer[Path(i).resolve()] for i in st.inputs
                     if Path(i).resolve() in producer]
            layer[st] = 1 + max((layer[p] for p in preds), default=-1)

        nodes = [{
            "id": st.name,
            "kind": getattr(st, "kind", "stage"),
            "description": getattr(st, "description", ""),
            "layer": layer[st],
            "inputs": [{"name": Path(i).name,
                        "external": Path(i).resolve() not in producer}
                       for i in st.inputs],
            "outputs": [Path(o).name for o in st.outputs],
        } for st in order]

        edges = []
        for st in self.stages:
            for i in st.inputs:
                key = Path(i).resolve()
                src = producer.get(key)
                if src is not None and src is not st:
                    edges.append({"src": src.name, "dst": st.name,
                                  "file": Path(i).name,
                                  "skip": layer[st] - layer[src] > 1})
        return {"name": self.name, "nodes": nodes, "edges": edges}

    def run(self, force: bool = False) -> dict[str, str]:
        """Execute in derived dependency order. Each skips itself if fresh."""
        results: dict[str, str] = {}
        for stage in self._dependency_order():
            t0 = time.time()
            status = stage.execute(force=force)
            results[stage.name] = status
            print(f"[{self.name}] {stage.name:<22} {status:<6} {time.time() - t0:5.1f}s")
        return results

    def test(self) -> dict[str, str]:
        """Run every stage's self_test(). 'pass' / 'no-test' / raises on failure."""
        results: dict[str, str] = {}
        for stage in self.stages:
            outcome = stage.self_test()
            results[stage.name] = "no-test" if outcome is None else "pass"
            print(f"[{self.name}] test {stage.name:<17} {results[stage.name]}")
        return results
