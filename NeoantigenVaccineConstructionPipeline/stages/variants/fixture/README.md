# Approach: fixture (didactic variant, no tools)

A native stage-2a source that emits a tiny, **explicitly illustrative** set of
annotated variants so the whole pipeline runs end-to-end today with no reads and
no tools. It is the counterpart to 2b's `known/` typer — but with one honest
difference stated up front.

## This is NOT a measurement

The default `KNOWN_GENOTYPES` in 2b are *real published germline genotypes* of the
benchmark cell lines. A somatic **call**, by contrast, is something you can only
get by running a caller on that sample's reads. So this fixture does **not** claim
its variant is present in HCC1395 (it isn't). It's a canonical textbook mutation
on a real reference protein, used purely to wire and test the 2a→3→… hand-off.

The real somatic calls come from [`../mutect2_vep/`](../mutect2_vep/) in Colab.

## The demo variant

| gene | change | transcript | locus (GRCh38) | WT source |
|---|---|---|---|---|
| **KRAS** | G12D | ENST00000311936 | chr12:25245350 C>T | UniProt P01116, res 1–20 |

`MTEYKLVVVGA[G]GVGKSALT` — position 12 is the glycine of the G12D hotspot. Because
the WT sequence is genuine human KRAS, a peptide built from it *is* a real KRAS
peptide; only the "present in this sample" claim is (correctly) withheld.

## Why it's legitimate for testing

The record's *shape* is exactly what VEP produces (SYMBOL, Feature, Amino_acids,
Protein_position, WildtypeProtein). Round-tripping it through
`base.write_annotated_vcf` → stage 3's `native/vcf.py` parser recovers the record
byte-for-byte — that round-trip is the stage's `self_test`. Swapping in the real
Mutect2+VEP source changes nothing downstream (same `somatic.annotated.vcf` shape).

Adding a variant: append a `VariantRecord` to `DEMO_VARIANTS`, or pass your own
list to `FixtureVariants(records=...)`. Keep WT sequences sourced to a real
protein — never invent one.
