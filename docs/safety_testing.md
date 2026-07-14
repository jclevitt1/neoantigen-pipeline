# Safety Testing for Neoantigen Vaccines — Notes & Resources

Working reference on how neoantigen-directed therapies are (and aren't) tested for
safety before humans, why a famous case slipped through, and what the human track
record actually looks like. Context for the pipeline's **stage 5 autoimmunity
filter** — the in-silico first pass whose ground truth is the wet lab.

---

## 0. First, the modality distinction (don't conflate these)

Two very different ways to aim T cells at cancer, with very different risk:

| | **Neoantigen vaccine** (what this pipeline designs) | **Adoptive TCR-T cell therapy** (the 2013 disaster) |
|---|---|---|
| Mechanism | Injects peptides/mRNA + adjuvant to *prompt the patient's own* T cells | Infuses *lab-engineered, self-replicating* killer T cells |
| Target | Patient's **private** tumor mutations (true neoantigens) | Often **shared/self** antigens (e.g. MAGE-A3) |
| Reversibility | Stop dosing; stimulus decays | Cells expand on their own; need a kill-switch |
| Risk profile | Mostly mild/transient so far | Can be fulminant and fatal |

**The 2013 titin case was the right-hand column, not a vaccine.** It's a cautionary
tale from a riskier cousin — instructive for our autoimmunity filter, but not a
failure of the vaccine approach.

---

## 1. The cardiovascular toxicity case (Linette / Cameron, 2013)

**What happened.** An affinity-enhanced TCR ("a3a") engineered to target
HLA-A*01–restricted **MAGE-A3** was given to two patients (one multiple myeloma,
one melanoma). Both died of **cardiogenic shock within ~4–5 days**. Autopsies showed
T-cell infiltration destroying heart muscle — but **no MAGE-A3 in the heart**.

**The mechanism.** The engineered TCR cross-reacted with an unrelated peptide from
**titin** — a giant protein in the contractile apparatus of striated (heart/skeletal)
muscle. The affinity enhancement that made the TCR better at hitting the tumor also
made it recognize the titin peptide, which the native TCR ignored. Confirmed later
by activating the T cells against **beating iPSC-derived cardiomyocytes**.

**Why preclinical testing missed it — the cell-STATE lesson.**
- **Mouse models are structurally blind.** The interaction is HLA-restricted (human
  peptide on human HLA-A*01). Mice have no human HLA and a different proteome, so
  they *cannot* reproduce it.
- **The human cell panels used the wrong STATE.** Cells present, on their MHC, a
  live sample of the proteins they're *currently* making and degrading. Titin is a
  **contraction** protein — a **beating** cardiomyocyte displays titin fragments; a
  **resting** cardiomyocyte sitting in a dish does not. Same cell *type*, different
  *state*, different surface display. The safety screens used cardiac cells that
  weren't beating → titin wasn't presented → the test looked clean. A patient's
  heart beats ~100,000×/day → titin always presented → attack.

**One-line takeaway:** testing the right cell *type* in the wrong *state* can give a
false "safe." What a cell shows the immune system is a function of what it's *doing*,
not just what it *is*.

---

## 2. Conceptual breakdown — what the wet lab tests, and what it misses

**What IS put in the dish**

- *Efficacy:* patient T cells / PBMCs (responders); antigen-presenting cells or
  peptide-pulsed targets (to read out activation via ELISpot / tetramer staining);
  tumor cells (kill target in cytotoxicity assays).
- *Safety:* a panel of normal primary human cells matched to the patient's HLA
  (hepatocytes, keratinocytes, endothelium, epithelium, renal, **cardiomyocytes**,
  neurons…); increasingly **iPSC-derived** cell types; motif-based proteome search
  + spot-testing of candidate cross-reactive peptides (the wet-lab twin of our
  stage-5 filter — this is how titin was found, *after* the deaths).

**What is NOT well covered (the accuracy frontier)**

1. **Cell state, not just type** — the titin lesson above. Resting dish cultures ≠
   working tissue (beating, load-bearing, inflamed, stressed).
2. **Context-dependent immunopeptidome** — inflammation / IFN-γ changes which
   peptides get cut (immunoproteasome) and displayed. "Clean in vitro" can be a
   false negative for the inflamed in-vivo state.
3. **Peptides invisible to sequence search** — proteasome-**spliced** peptides
   (stitched from two non-adjacent fragments) and **post-translationally modified**
   peptides. Missed by naive proteome search *and* by our filter.
4. **HLA restriction blinds animal models** — mice lack human HLA; humanized/HLA-
   transgenic mice patch one allele at a time.
5. **Restricted / privileged expression** — developmental, testis-only
   (cancer-testis antigens like MAGE), or immune-privileged-site antigens aren't
   represented by panels of cultured adult cells.
6. **No tissue architecture / physiology** — 3D structure, flow, mechanics,
   cross-organ effects.

**Where the field is pushing:** mass-spec **immunopeptidomics** (physically sequence
what a cell actually presents, catching spliced/modified peptides), **iPSC
organoids / organ-on-chip** (right cells in the right *state*), **humanized mouse
models**, and better computational cross-reactivity prediction (our filter is the
toddler version).

---

## 3. Human track record — successes since 2013

The 2013 deaths were adoptive TCR-T against a shared antigen. **Neoantigen
vaccines** specifically have a growing record of *successes* (no completed Phase 3
yet as of mid-2026; first approvals possibly late 2026–2027):

- **2017 — first-in-human feasibility (melanoma).** Ott et al. and Sahin et al.
  showed personalized neoantigen vaccines could raise neoantigen-specific T cells in
  patients.
- **Melanoma — mRNA-4157 / V940 / intismeran autogene (Moderna + Merck).**
  KEYNOTE-942 Phase 2b met its endpoint: + pembrolizumab, 18-mo recurrence-free
  survival **79% vs 62%**. 3-year update sustained. **Phase 3 running** (melanoma,
  NSCLC, cutaneous SCC).
- **Pancreatic / PDAC — autogene cevumeran (BioNTech + Genentech).** Phase 1: raised
  neoantigen-specific T cells in **8/16** patients; those cells **persisted >3 years**
  and responders had prolonged recurrence-free survival. Randomized Phase 2 ongoing.

**Bottom line:** the modality that killed those two patients ≠ the modality this
pipeline designs. Vaccines are more reversible (stop dosing; no self-replicating
agent), and their human results trend positive — while the titin case remains the
sharpest argument for why the autoimmunity screen exists.

---

## 4. Resources

**The cardiovascular toxicity case**
- Linette et al., *Blood* 2013 — clinical report (the two deaths): https://pubmed.ncbi.nlm.nih.gov/23770775/ · full text: https://pmc.ncbi.nlm.nih.gov/articles/PMC3743463/
- Cameron et al., *Sci Transl Med* 2013 — titin identified as the cross-reactive target: https://www.science.org/doi/10.1126/scitranslmed.3006034
- *Blood* editorial, "TCR takes to titin" (plain-language): https://ashpublications.org/blood/article/122/6/853/32216/Genetic-engineering-of-T-cell-receptors-TCR-takes
- *Scientific Reports* 2016 — direct molecular mimicry confirmed with beating cardiomyocytes: https://www.nature.com/articles/srep18851

**Neoantigen vaccine successes / reviews**
- mRNA-4157/V940 Phase 2b (KEYNOTE-942) announcement (Merck): https://www.merck.com/news/moderna-and-merck-announce-mrna-4157-v940-an-investigational-personalized-mrna-cancer-vaccine-in-combination-with-keytruda-pembrolizumab-met-primary-efficacy-endpoint-in-phase-2b-keynote-94/
- 3-year update, intismeran autogene (mRNA-4157) + pembrolizumab, *JCO Oncology Advances*: https://ascopubs.org/doi/10.1200/OA-25-00008
- Autogene cevumeran, long-lived T cells in PDAC, *Nature* 2024: https://www.nature.com/articles/s41586-024-08508-4
- BioNTech 3-year Phase 1 follow-up (pancreatic): https://investors.biontech.de/news-releases/news-release-details/three-year-phase-1-follow-data-mrna-based-individualized
- Review — advances in personalized neoantigen therapies, *J Exp Med* 2026: https://rupress.org/jem/article/223/2/e20241234/278560/Advances-in-the-development-of-personalized

**Background reviews (safety / cross-reactivity)**
- Personalized neoantigen cancer vaccines — progress, challenges: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11427492/
- mRNA vaccines in oncology (neoantigen targeting): https://pmc.ncbi.nlm.nih.gov/articles/PMC13064569/
