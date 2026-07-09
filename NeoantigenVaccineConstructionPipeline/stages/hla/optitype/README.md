# Approach: OptiType

**OptiType** infers the 4-digit HLA-I genotype (HLA-A/-B/-C) directly from
sequencing reads by mapping them to a reference of known HLA allele sequences and
solving for the most likely pair at each gene. Well validated on DNA and RNA.
Alternatives: arcasHLA (RNA-oriented), HLA-HD, Polysolver.

Output we normalize to: `hla.json` = `{"alleles": ["HLA-A*02:01", "HLA-A*01:01",
"HLA-B*07:02", ...]}`. `RankStage` reads this list and scores every candidate
peptide against each allele.

**Status:** not implemented. MVP shortcut: HLA types for benchmark cell lines
(HCC1395, COLO829) are published — we can hardcode a real `hla.json` for the demo
Case instead of running the typer.

**Tool:** [OptiType](https://github.com/FRED-2/OptiType).
