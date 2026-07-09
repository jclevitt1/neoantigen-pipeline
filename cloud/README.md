# Running in the cloud (Google Colab)

The disk-cheap, download-nothing-locally setup. Data lives in the cloud; you slice
a region on demand into ephemeral Colab scratch. Code stays in git (kilobytes);
only tiny persistent bits go to Google Drive.

## The split

| Thing | Where | Size |
|---|---|---|
| Pipeline **code** | GitHub → cloned into Colab | KB |
| **Sample** BAM slice (chr21) | Colab scratch (ephemeral) | ~100s MB |
| **Shared** refs (genome, proteome, model pickle) | Google Drive (persistent) | small (proteome ~30 MB) |
| Full BAMs, whole genome | **never stored** — sliced on demand | — |

## Colab cells

**1. Install tools**
```bash
!apt-get -qq install -y samtools bcftools tabix >/dev/null
!samtools --version | head -1
```

**2. Get the code** (push this repo to a private GitHub first)
```bash
!git clone https://github.com/<you>/neoantigen_pipeline.git
%cd neoantigen_pipeline
!pip -q install scikit-learn pandas   # for the stage-4 ranker
```

**3. Persist the small shared bits on Drive**
```python
from google.colab import drive
drive.mount('/content/drive')
# put proteome.fa + the model pickle under e.g. /content/drive/MyDrive/neo/refs/
```

**4. Build a Case pointing at scratch + Drive, then run acquire**
```python
from pathlib import Path
from NeoantigenVaccineConstructionPipeline.case import Case
from NeoantigenVaccineConstructionPipeline.stages.acquire.acquire_stage import AcquireStage
from NeoantigenVaccineConstructionPipeline.stages.acquire import (
    Seqc2SliceSource, seqc2_wes_dna_manifest,
)

case = Case(
    sample_id="HCC1395",
    workdir=Path("/content/work"),                       # ephemeral scratch
    # raw files live under raw/ — MUST differ from the normalized *_bam paths
    # (workdir/tumor_dna.bam), or acquire and input would "produce" the same file
    tumor_dna=Path("/content/work/raw/tumor_dna.bam"),
    normal_dna=Path("/content/work/raw/normal_dna.bam"),
    tumor_rna=Path("/content/work/raw/tumor_rna.bam"),   # RNA: separate follow-up
    reference=Path("/content/drive/MyDrive/neo/refs/GRCh38.chr21.fa"),
    proteome=Path("/content/drive/MyDrive/neo/refs/proteome.fa"),
)

# Verified SEQC2 WES DNA URLs (tumor + normal). RNA is deferred (needs STAR align).
manifest = seqc2_wes_dna_manifest(center="EA")   # WES_EA_T_1 / WES_EA_N_1 .bwa.dedup.bam
# Confirm contig naming once:  !samtools view -H {manifest['tumor_dna']} | grep '@SQ' | head
AcquireStage(case, source=Seqc2SliceSource(manifest, region="chr21")).execute()
!ls -lh /content/work/raw
```

Expected: tumor + normal chr21 BAM slices (+ `.bai`) in `/content/work/raw`, a few
hundred MB total — not a byte on your laptop. (RNA follows once we align it.)

## Cost

- **Colab free:** $0. ~12 GB RAM, ~100 GB scratch, ~12 h sessions — enough for a
  chr21 run. Colab Pro (~$10/mo) only for longer/background sessions.
- Graduating later to a spot VM + GCS bucket runs the *same code*, ~<$1/experiment
  when you shut the VM down.

## Open items before a live pull
1. Confirm the exact SEQC2 aligned-BAM URLs (and that a `.bai` is co-located) —
   see `stages/acquire/seqc2_slice/README.md`.
2. Stage `GRCh38.chr21.fa` + `proteome.fa` + the stage-4 model pickle on Drive
   (one-time). A `setup_references` helper is the next thing to add here.
