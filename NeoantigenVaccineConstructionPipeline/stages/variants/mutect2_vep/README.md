# Approach: Mutect2 (call) + VEP (annotate)

**Call — GATK Mutect2.** The de-facto standard somatic caller. Runs in
tumor-with-matched-normal mode: the normal BAM is passed as the germline control so
inherited variants are subtracted out. Followed by `FilterMutectCalls` to flag
low-confidence calls. Alternatives: Strelka2, VarScan2.

**Annotate — Ensembl VEP.** Reads the VCF, and for each variant reports the gene,
transcript, and protein consequence (missense / frameshift / stop-gain / silent),
writing it back into the VCF as a `CSQ` field. Alternative: SnpEff (writes `ANN`).
Needs a reference annotation (GENCODE/Ensembl).

## Why annotation is folded onto the tail here

Stage 3 translates mutations into peptides. It needs to know the *protein*
consequence, not just the genome coordinate. Doing annotation at the end of 2a
means the VCF handed downstream is self-describing — stage 3 reads consequences
instead of re-computing them.

**Status:** not implemented. MVP plan: run on a **single-chromosome subset** of
HCC1395/HCC1395BL so a real call completes fast on a laptop.

**Tools:** [GATK/Mutect2](https://gatk.broadinstitute.org/) · [Ensembl VEP](https://www.ensembl.org/vep) · benchmark truth set: SEQC2 (HCC1395).
