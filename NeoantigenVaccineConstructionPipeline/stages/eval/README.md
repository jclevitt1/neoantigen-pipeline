# Stage 6 — Eval Filters

**Job:** judge each ranked peptide on three safety/practicality axes and attach
verdicts. It **flags, it does not drop** — stage 5 builds only from survivors. This
is the "6 gates 5" relationship.

## The three filters (and why each matters)

- **Autoimmunity** — does the peptide look like a *normal self-protein*? If a
  vaccine raised T cells against it, they could attack healthy tissue. This is the
  computational stand-in for the disaster in `../../docs/safety_testing.md` (the
  titin case). The real method is a proteome-wide near-match (BLAST); our MVP proxy
  is an **exact substring match** against the human proteome.
- **Clonality** — is the mutation in *every* tumor cell (**clonal**) or only *some*
  (**subclonal**)? Clonal is a better target: hit it and you hit every cancer cell.
  Measured by the **cancer cell fraction (CCF)**, derived from the mutation's
  variant allele frequency in the VCF.
- **Manufacturability** — can the peptide physically be synthesized/dissolved?
  Sequence physicochemistry: too hydrophobic → aggregates; multiple cysteines →
  disulfide/aggregation.

## Why native, and why not pluggable

This is *our* code (a NATIVE stage), and the filters are a fixed, well-understood
rule set — unlike ranking, there's no bake-off of competing "approaches" worth an
interface. So there's a single `rule_based/` approach. If a fundamentally different
method appears (e.g. a learned autoimmunity model), it becomes a new subdir.

## I/O contract

| | |
|---|---|
| **Inputs** | `ranked.tsv` (from stage 4), `proteome` (external FASTA, self-check) |
| **Outputs** | `filtered.tsv` — every input row + `autoimmunity_flag`, `clonality`, `manufacturability` |
| **Dry checks** | input TSV has `peptide` + valid proteome FASTA; output has the flag columns |
| **Survivors** | `autoimmunity_flag == False` **and** `manufacturability == "pass"` (clonal preferred) |

The Stage auto-runs a `self_test` on build (native stages get hard fixture
assertions).

## Approaches

- [`rule_based/`](rule_based/) — the three filters as plain functions + thresholds.
