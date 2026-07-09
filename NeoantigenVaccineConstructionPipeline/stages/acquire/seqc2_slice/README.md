# Approach: SEQC2 region-slice

Pull one genomic **region** from the remote SEQC2 aligned BAMs — no full download.

```
samtools view -b -h <remote_bam_url> chr21 -o tumor_dna.bam   # then: samtools index
```

## Verified locations (browsed 2026-07)

SEQC2 (SRA **SRP162370**) published BWA-MEM–aligned, **indexed** WES BAMs. Both
`.bam` and a co-located `.bai` are present → remote slicing works.

- **Base (DNA WES):**
  `https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/seqc/Somatic_Mutation_WG/data/WES`
- **Pattern:** `WES_<CENTER>_<T|N>_<rep>.bwa.dedup.bam` (+ `.bai`)
  - centers with matched T/N pairs: `EA`, `FD`, `IL`, `LL`, `NC`, `NV`
- **Default demo pair:**
  - tumor (HCC1395): `WES_EA_T_1.bwa.dedup.bam`
  - normal (HCC1395BL): `WES_EA_N_1.bwa.dedup.bam`

Build the DNA manifest with the helper:

```python
from NeoantigenVaccineConstructionPipeline.stages.acquire import (
    Seqc2SliceSource, seqc2_wes_dna_manifest,
)
manifest = seqc2_wes_dna_manifest(center="EA")     # {tumor_dna, normal_dna}
src = Seqc2SliceSource(manifest, region="chr21")
AcquireStage(case, source=src).execute()
```

Partial manifests are allowed — DNA-only is the current MVP path.

## Tumor RNA is NOT here (separate follow-up)

The somatic FTP tree has only DNA (WES/WGS). SEQC2 RNA-seq is raw **FASTQ** under
SRA **SRX8401273–5** (BioProject **PRJNA635123**) — it needs a STAR alignment
before it's a sliceable BAM. So RNA is deferred; stage-3 expression tagging is a
starter until the RNA BAM exists.

## Two confirmations before / at a live pull
1. **Contig naming** — is it `chr21` or `21`? One command:
   `samtools view -H <url> | grep '@SQ' | head` → set `region` to match.
2. **Index resolution** — the index is `…dedup.bai` (Picard-style). htslib finds
   both `…bam.bai` and `…bai`; if a remote read can't locate it, pass it explicitly.

## Links
- Project: https://www.ncbi.nlm.nih.gov/sra/?term=SRP162370
- FTP data root: https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/seqc/Somatic_Mutation_WG/data/
- SEQC2 sequencing overview: https://sites.google.com/view/seqc2/home/sequencing

`source.py` → `Seqc2SliceSource`, `seqc2_wes_dna_manifest()`. Default region: `chr21`.
