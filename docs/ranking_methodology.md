# Stage 4 (Rank) — Neoantigen Ranking Methodology & Model Selection

Working reference on *how* to rank neoantigen candidates, *why* the ordering of the
scoring matters, and *which* published models we considered for each axis (and why we
picked what we picked). Context for the pipeline's **stage 4 rank step**, which today
uses a single homegrown logistic regression and is being modernized behind a pluggable
scoring seam.

The governing constraint on every tool choice below: the pipeline must run **free,
offline, pip-installable, and redistributable** inside Google Colab. A more accurate
model we cannot legally ship, or cannot run without a license server, is not a candidate.

---

## 0. The two-axis mental model

The field has converged on decomposing "is this a good neoantigen?" into two questions,
plus a set of modulators:

1. **Presentation (Axis 1) — "Will this mutant peptide be displayed on the patient's
   MHC-I at all?"** A processing/binding problem. **Well predicted** by modern tools.
2. **Immunogenicity / recognition (Axis 2) — "Given that it IS presented, will a CD8+
   T cell actually respond to it?"** A TCR-recognition problem. **Still weak** — neutral
   benchmarks top out around AUC ≈ 0.6.
3. **Modulators (gates, not scores):** expression (an unexpressed neoantigen is invisible
   no matter how well it binds) and clonality (a clonal/truncal mutation present in every
   tumor cell beats a subclonal one).

---

## 1. The central design decision: **condition recognition on presentation** (gate, then rank)

This is the most important methodological point to record, because it contradicts how the
current single logistic regression works.

**The finding.** In the TESLA consortium benchmark (Wells et al., *Cell* 2020), >36 groups
each submitted ranked neoantigen predictions for shared melanoma/NSCLC samples; 608 peptides
were then experimentally tested for pMHC binding and T-cell recognition. The decisive result:

> Teams that prioritized **foreignness or agretopicity *without first conditioning on
> presentation* did no better than chance.** Immunogenicity/recognition features only carry
> signal on peptides that are actually presented. The winning recipe was "rank by
> *presented AND recognized*, then by binding affinity" — which reached **precision >70% at
> ~45% recall** and filtered ~98% of non-immunogenic peptides.

TESLA's five empirically-validated key parameters: (1) MHC **binding affinity**, (2) **tumor
abundance** (RNA expression), (3) **binding stability**, (4) **fraction hydrophobic** at
TCR-facing residues, (5) **mutation position** within the peptide.

- Wells et al., *Cell* 2020 — "Key Parameters of Tumor Epitope Immunogenicity Revealed
  Through a Consortium Approach Improve Neoantigen Prediction":
  https://www.cell.com/cell/fulltext/S0092-8674(20)31156-9
  (open PDF: https://escholarship.org/content/qt8094s6nw/qt8094s6nw.pdf)

**The consequence for our design — two stages, not one blended model:**

- **Stage A — presentation gate (hard rules).** Filter on binding %rank + expression +
  clonality. Candidates that fail are tiered out, not rescued.
- **Stage B — recognition score (on survivors only).** Rank the peptides that clear the
  gate, using the immunogenicity axis.

**Why our current setup is wrong.** A single flat logistic regression over all features lets
a high foreignness/immunogenicity score numerically compensate for a peptide that will never
reach the cell surface (unexpressed, or a non-binder). That is precisely the failure mode
TESLA punishes. Gating first makes the recognition score meaningful.

**The corroborating model — Łuksza neoantigen fitness.** Łuksza et al. (*Nature* 2017, updated
*Nature* 2022) independently encode the same structure: neoantigen quality = **amplitude ×
recognition**.
- **Amplitude A = presentation term = Kd_WT / Kd_MT** (agretopicity — how much better the
  mutant binds than its tolerized wild-type). This is the presentation-conditioning term.
- **Recognition R = TCR cross-reactivity term** — alignment similarity of the neopeptide to
  known immunogenic epitopes (IEDB), passed through a steep sigmoid (inverse-temperature
  k ≈ 4.87). The 2022 update adds a self-distance term C (quality Q = R × D, D = log A + log C).
- Łuksza 2017: https://www.nature.com/articles/nature24473 · PMC:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC6137806/
- Łuksza 2022 (immunoediting in pancreatic-cancer survivors):
  https://www.nature.com/articles/s41586-022-04735-9 · code:
  https://github.com/LukszaLab/NeoantigenEditing

**One-line takeaway:** presentation is a filter you apply *first*; recognition is a re-ranking
you apply *only to what survives*. Never let recognition rescue an un-presented peptide.

---

## 2. The feature checklist (what a modern ranker computes)

Consensus features, tagged by axis, each with the paper that established its importance.

| Feature | Axis | Established by |
|---|---|---|
| MHC-I binding affinity / **presentation %rank** (mutant) | Presentation | TESLA; every tool |
| Binding **stability** (pMHC half-life) | Presentation | TESLA |
| **Presentation likelihood** (mass-spec / eluted-ligand %rank) | Presentation | MHCflurry 2.0; Immunity 2023 |
| Antigen **processing** (proteasomal cleavage, TAP) | Presentation | NetChop; pTuneos |
| **Agretopicity / DAI** = Kd_WT / Kd_MT | Immunogenicity | Łuksza 2017; TESLA (only helps *after* presentation) |
| **Foreignness** (similarity to known immunogenic/IEDB epitopes) | Immunogenicity | Łuksza 2017/2022 |
| **Dissimilarity-to-self** (distance from human proteome) | Immunogenicity | Richman 2019; Łuksza 2022 |
| **Fraction hydrophobic** at TCR-contact (non-anchor) residues | Immunogenicity | TESLA |
| **Mutation position** (anchor vs. TCR-facing) | Gate/flag | TESLA; pVACseq "Anchor" tier |
| **RNA expression** (TPM); **allele expression** = TPM × RNA VAF | Modulator (gate) | TESLA; pVACseq |
| **Clonality** (DNA VAF; clonal vs. subclonal) | Modulator (gate) | Łuksza; pVACseq "Subclonal" tier |

The two highest-leverage features to add ourselves — **agretopicity (DAI)** and
**dissimilarity-to-self** — are nearly free in our pipeline: we already run MHC binding for
Axis 1 (so mutant-vs-WT is a ratio we can compute), and we already load the human proteome
for the stage-5 autoimmunity filter (so dissimilarity-to-self is a k-mer/BLOSUM lookup we can
reuse). Given the ~0.6 immunogenicity ceiling, this concept layer matters more than the exact
classifier.

Supporting benchmark/context:
- Müller, Gfeller et al., *Immunity* 2023 — harmonized datasets + ML improve ranking up to
  ~30%; new features (presentation hotspots, binding promiscuity, oncogenicity):
  https://www.cell.com/immunity/fulltext/S1074-7613(23)00406-5
- Richman et al., *Cell Systems* 2019 — dissimilarity-to-self:
  https://www.cell.com/cell-systems/fulltext/S2405-4712(19)30307-2
- Ghorani et al., *Ann Oncol* 2018 — DAI + affinity vs survival across 6,324 patients:
  https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5834109/

---

## 3. Models considered — Axis 1 (presentation)

The field-wide shift here is **binding affinity (BA, IC50 in nM) → eluted-ligand /
presentation (EL, mass-spec)**. EL data captures the whole pathway (cleavage, TAP, real
allele-specific motifs), not just "can it sit in the groove." We want an **EL/presentation
score**, ideally with a %rank, not a raw IC50.

| Tool | Data | Offline / pip? | License | Verdict for us |
|---|---|---|---|---|
| **MHCflurry 2.0** | affinity + processing + **presentation (EL)** | **`pip install mhcflurry` + fetch; offline; CPU-fine** | **Apache-2.0 (redistributable, commercial OK)** | **CHOSEN.** Only tool meeting all four constraints. |
| NetMHCpan-4.1 / 4.2 EL | BA + EL, ~230 alleles | standalone binary, not pip | **DTU academic; NOT redistributable** | Accuracy reference only; user-installed optional backend, never bundled. |
| BigMHC_EL | EL (MS), 7-net ensemble | git clone ~5 GB, PyTorch | Academic | Optional high-accuracy backend; too heavy for default. |
| MixMHCpred 3.0 | EL immunopeptidomics | wrapper, needs MAFFT, not pip | Free academic; **separate commercial license** | License friction; not for a redistributable pipeline. |
| ImmuneApp / HLApollo / TransPHLA / ESM-based | EL / binding | research-grade, not turnkey | mixed | Promising, not deployable-clean yet. |
| HLAthena | EL (mono-allelic MS) | **web-only** | academic | Not deployable offline. |

**Why MHCflurry 2.0 wins.** (a) Apache-2.0 — we can legally redistribute it, academic *or*
commercial; this alone eliminates most rivals. (b) `pip install` + one-time weight fetch, then
fully offline in Colab, no server, no GPU. (c) Outputs an inspectable `presentation_score`
(0–1) + percentile + separate affinity/processing columns. (d) Optionally consumes N/C-terminal
flanks → the processing signal our homegrown model lacks. (e) Its presentation head is *itself*
a logistic regression over (affinity, processing) trained on mass-spec — i.e. a
professionally-trained version of exactly what we already built, making it the cleanest drop-in.

- MHCflurry 2.0 — GitHub: https://github.com/openvax/mhcflurry · PyPI:
  https://pypi.org/project/mhcflurry/ · *Cell Systems* 2020:
  https://www.sciencedirect.com/science/article/pii/S2405471220302398
- NetMHCpan-4.1 — *NAR* 2020: https://academic.oup.com/nar/article/48/W1/W449/5837056 ·
  service (license): https://services.healthtech.dtu.dk/services/NetMHCpan-4.1/
- BigMHC — GitHub: https://github.com/KarchinLab/bigmhc · *Nat Mach Intell* 2023:
  https://www.nature.com/articles/s42256-023-00694-6

---

## 4. Models considered — Axis 2 (immunogenicity / recognition)

This axis is genuinely weak (neutral melanoma-neoepitope benchmark: best AUC ≈ 0.60,
https://www.frontiersin.org/journals/immunology/articles/10.3389/fimmu.2023.1094236/full).
Treat any classifier as a **soft re-ranking prior, never a hard gate.** Known reasons it stays
weak: tiny/biased positive sets (hundreds of validated immunogenic neoantigens), private TCR
repertoires the peptide-only models can't see, and training-domain mismatch (many tools were
trained on tryptophan-enriched *viral* epitopes that don't transfer to neoepitopes).

| Tool | Predicts / features | Offline / pip? | License | Verdict for us |
|---|---|---|---|---|
| **DeepImmuno-CNN** | pMHC immunogenicity CNN (9–10mers) | **`pip install git+…`; Colab-native; CPU-fine** | **MIT (commercial OK)** | **CHOSEN as default / commercial-safe.** Weaker but the only strong MIT + pip option. |
| **BigMHC_IM** | transfer-learned immunogenicity; highest reported precision on true neoepitopes | git clone ~5 GB, PyTorch, offline | **Academic (non-commercial, copyleft-ish)** | **CHOSEN as accuracy backend** *if* non-commercial. Do NOT ship if commercial use is possible. |
| ICERFIRE 1.0 | RF on ICORE, agretopicity, self-similarity, expression; best cross-dataset generalization | standalone, not pip | Academic (DTU) | Strong reference for *which features* to encode; license/packaging friction. |
| PRIME2.0 | presentation × TCR-facing residues | offline, not pip; needs MixMHCpred in PATH | **Academic-only** | Community baseline; MixMHCpred dependency reintroduces license friction. |
| Łuksza fitness | foreignness × agretopicity (quality score, not a classifier) | offline (Python) | Academic/open | **Adopted as the composite recipe** (see §5), not as a black-box model. |
| IEDB (Calis 2013) | position-weighted AA model | offline | free non-commercial | Superseded baseline; viral-trained, weak transfer. |
| Repitope / ImmugenX / NetTCR / NeoaPred / ImmunoStruct | TCR-contact / PLM / structure / TCR-aware | R or research code / need TCR or structure inputs | mixed | Future options; too heavy or need inputs we don't have (patient TCR repertoire, structures). |

**Why this pair.** The choice is governed by licensing posture, not just accuracy: **DeepImmuno**
(MIT, pip, Colab-native) is the portable/commercial-safe default; **BigMHC_IM** is the accuracy
upgrade for non-commercial use. But per §2, the biggest win on this axis is not the classifier —
it is computing **agretopicity (DAI)** and **dissimilarity-to-self** ourselves, which is license-
free and, given the 0.6 ceiling, carries more signal than swapping classifiers.

- DeepImmuno — GitHub: https://github.com/frankligy/DeepImmuno · *Brief Bioinform* 2021:
  https://academic.oup.com/bib/article/22/6/bbab160/6261914
- BigMHC_IM — GitHub: https://github.com/KarchinLab/bigmhc · *Nat Mach Intell* 2023:
  https://www.nature.com/articles/s42256-023-00694-6
- ICERFIRE 1.0 — https://services.healthtech.dtu.dk/services/ICERFIRE-1.0/ · *NAR Cancer* 2024:
  https://academic.oup.com/narcancer/article/6/1/zcae002/7591107
- PRIME2.0 — GitHub: https://github.com/GfellerLab/PRIME · *Cell Systems* 2023:
  https://www.cell.com/cell-systems/fulltext/S2405-4712(22)00470-7

---

## 5. The chosen design — gate, then composite, behind a pluggable seam

Reference framework: **pVACtools / pVACseq** (Griffith Lab, BSD-3) is the canonical integrating
pipeline — it wraps the binding/immunogenicity predictors and emits a tiered, columnar
aggregated report (Pass / Anchor / Subclonal / LowExpr / PoorBinder), with agretopicity as a
"fold change" column and expression/clonality as hard gates. We **borrow its aggregation design
without adopting the whole tool**, because its NetMHCpan dependency reintroduces the
non-redistributable license we are avoiding.
- pVACtools: https://github.com/griffithlab/pVACtools · docs: https://pvactools.readthedocs.io/
  · *Cancer Immunol Res* 2020: https://aacrjournals.org/cancerimmunolres/article/8/3/409/469797

**The two-stage ranker:**

```
Stage A — presentation gate (hard rules, tiered out if failed):
    MHCflurry presentation_score %rank  +  expression (TPM × RNA VAF)  +  clonality (DNA VAF)

Stage B — recognition composite (on survivors only):
    default = Łuksza fitness   Q = R × D,   D = log(A) + log(C)
      A = agretopicity (DAI = mutant/WT MHC binding)   ← we compute (Axis-1 outputs)
      R = foreignness (BLAST vs IEDB immunogenic set, sigmoid k ≈ 4.87)
      C = self-distance (dissimilarity to WT/self)     ← we compute (reuse proteome)
    optionally × TESLA hydrophobicity/stability factors
```

**Pluggable seam — expose swappable strategies:**
- `LogRegNeopepStrategy` — the current homegrown model, kept as the zero-dependency baseline.
- Composite (Łuksza/TESLA) — the transparent default: training-free, reproducible, TESLA-
  consistent, and doesn't inherit the ML overfitting the 2025 literature warns about.
- `DeepImmunoStrategy` / `BigMHCImStrategy` — optional learned backends for the ~10–30% upside
  *when* you trust your labels; chosen by licensing posture.
- A feature-augmenting wrapper that adds DAI + dissimilarity-to-self on top of any base model —
  where most of the real lift lives.

**Recommended upgrade path (smallest first):**
1. Swap the homegrown logistic regression → **MHCflurry `presentation_score`** (drop-in win).
2. Add **agretopicity (DAI)** + **dissimilarity-to-self** as computed feature columns (nearly
   free, biggest signal-per-effort).
3. Add the **Łuksza composite** as the default Axis-2 ranker; keep a learned strategy
   (DeepImmuno / BigMHC_IM) as an optional backend.

---

## 6. Resources

**Benchmarks / feature importance**
- TESLA / Wells et al., *Cell* 2020: https://www.cell.com/cell/fulltext/S0092-8674(20)31156-9
- Łuksza et al., *Nature* 2017: https://www.nature.com/articles/nature24473
- Łuksza et al., *Nature* 2022: https://www.nature.com/articles/s41586-022-04735-9
- Müller/Gfeller, *Immunity* 2023: https://www.cell.com/immunity/fulltext/S1074-7613(23)00406-5
- Neutral benchmark / limitations, *Front Immunol* 2023:
  https://www.frontiersin.org/journals/immunology/articles/10.3389/fimmu.2023.1094236/full

**Presentation predictors (Axis 1)**
- MHCflurry 2.0: https://github.com/openvax/mhcflurry ·
  https://www.sciencedirect.com/science/article/pii/S2405471220302398
- NetMHCpan-4.1: https://academic.oup.com/nar/article/48/W1/W449/5837056
- BigMHC: https://github.com/KarchinLab/bigmhc · https://www.nature.com/articles/s42256-023-00694-6

**Immunogenicity predictors (Axis 2)**
- DeepImmuno: https://github.com/frankligy/DeepImmuno ·
  https://academic.oup.com/bib/article/22/6/bbab160/6261914
- BigMHC_IM: https://github.com/KarchinLab/bigmhc
- ICERFIRE 1.0: https://academic.oup.com/narcancer/article/6/1/zcae002/7591107
- PRIME2.0: https://github.com/GfellerLab/PRIME
- DAI / dissimilarity-to-self: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5834109/ ·
  https://www.cell.com/cell-systems/fulltext/S2405-4712(19)30307-2

**Integrating frameworks**
- pVACtools: https://github.com/griffithlab/pVACtools · https://pvactools.readthedocs.io/
- NeoPredPipe: https://github.com/MathOnco/NeoPredPipe
- MuPeXI: https://github.com/ambj/MuPeXI
- ImmuneMirror: https://github.com/weidai2/ImmuneMirror
