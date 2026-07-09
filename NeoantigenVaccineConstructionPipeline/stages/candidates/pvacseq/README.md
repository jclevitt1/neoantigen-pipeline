# Approach: pVACseq

**pVACseq** (part of the pVACtools suite) reads the annotated somatic VCF, and for
each protein-altering mutation generates all mutant peptide windows of the
requested lengths (8–11mers), pairing each with its wild-type counterpart. It can
also call binding internally, but in our DAG we keep binding in stage 4 so the
scoring approach stays swappable.

**Expression tag:** join TPM per gene/transcript from the tumor RNA — computed with
a quantifier (Salmon/RSEM/featureCounts) over the RNA BAM — onto each candidate.

**Status:** not implemented. MVP shortcut: from a single-chromosome variant subset,
generate a handful of real candidate windows so stage 4 has honest input; or
hand-write a small `candidates.tsv` fixture with `peptide`,`tpm`,`ccf` columns.

**Tools:** [pVACtools/pVACseq](https://pvactools.readthedocs.io/) · [Salmon](https://salmon.readthedocs.io/) for TPM.
