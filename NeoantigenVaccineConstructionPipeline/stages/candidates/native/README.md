# Approach: native (our own window generator)

The "we own it" approach — no pVACseq. It's small enough to read, and it's the
part of stage 3 worth understanding in full, so it's built natively and
hard-tested from the stage's `self_test`.

## The pipeline inside the stage

```
annotated VCF ──vcf.py──▶ variant dicts ──windows.py──▶ candidate peptides ──┐
                                                                             ├─▶ candidates.tsv
tumor RNA (deferred) ──expression.py──▶ tpm tag ────────────────────────────┘
```

### `windows.py` — the heart (pure, no I/O)
1. **`apply_substitution`** — build the mutant protein: take the wild-type
   sequence, change one residue (`G12D`). A `ref_aa` guard catches VCF/transcript
   desync before it produces garbage.
2. **`windows_covering`** — every 8/9/10/11-mer that *covers* the mutated
   position. A window that doesn't touch the mutation equals a normal human
   peptide, so it's dropped. Deterministic order, ends handled.

### `vcf.py` — annotated-VCF reader (plain text, no pysam)
Reads the `CSQ` subfield order from the `##INFO=<ID=CSQ ... Format: ...>` header
(order isn't fixed across VEP runs) and pulls, per protein-altering transcript:
`SYMBOL, Feature, Amino_acids (ref/alt), Protein_position, WildtypeProtein`.
The `WildtypeProtein` string is what a VEP protein plugin adds — the same input
pVACseq relies on. One variant hitting N transcripts yields N candidate sets.

### `expression.py` — pluggable TPM tag
`ExpressionSource` seam (like `Ranker`/`AcquireSource`):
- **`PlaceholderExpression`** (default) — no RNA yet: `tpm='NA'`, keeps every row,
  never invents a number. Needs no inputs, so stage 3 runs today on the VCF alone.
- **`FeatureCountsExpression`** (stub) — the real one; declares the RNA BAM as a
  required input, so wiring it in makes the `1-input → 3-candidates` edge real and
  lets the stage drop candidates below `tpm_min`.

## Scope (MVP)
Handles **missense** substitutions. Frameshift / inframe-indel neoantigens need
the VEP Downstream plugin to supply the novel reading frame; the window logic
generalizes to them unchanged once `vcf.py` extracts that sequence — a documented
extension, not a rewrite.

## vs. `../pvacseq/`
pVACseq does the same window generation wrapped as an external tool. We keep it
native so the logic is legible and testable now; pVACseq stays documented as the
production-scale alternative.
