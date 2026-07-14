"""
file_docs.py — human documentation for every file that flows through the pipeline.

The DAG (core) knows a file's *name*, who *produces* it, and who *consumes* it —
all structural, all derived. What it can't know is what the file biologically
*is* and *how* it's generated. That lives here, keyed by the Case's logical path
name (the same attribute a stage references, e.g. `somatic_vcf`), so this registry
sits right next to the schema it documents (case.py).

`build_file_docs(case)` resolves those logical names to the *actual* basenames in
a given Case and returns a `{basename: doc}` map. viz overlays it generically: a
documented file chip becomes clickable and opens a "what / how / produced-by /
consumed-by" popover. External raw inputs (whose filenames vary by data source)
resolve correctly because the Case knows their real paths.

Nothing here is measured data — these are role/format descriptions of the
contract files, safe to show verbatim.
"""
from __future__ import annotations

# doc = {title, format, what, how}. Keyed by Case logical path name.
FILE_DOCS: dict[str, dict[str, str]] = {
    # ---- external roots (supplied to the pipeline, produced by no stage) ----
    "tumor_dna": {
        "title": "Tumor DNA — raw reads",
        "format": "FASTQ / BAM / CRAM (source-dependent)",
        "what": "The cancer's genome as sequenced from a tumor sample. One half of "
                "the tumor-vs-normal comparison that reveals somatic (tumor-only) mutations.",
        "how": "Supplied externally (e.g. SRA/GDC download in stage 0). A pipeline "
               "root — not produced by any stage.",
    },
    "normal_dna": {
        "title": "Normal DNA — raw reads",
        "format": "FASTQ / BAM / CRAM (source-dependent)",
        "what": "The patient's inherited (germline) genome, usually from blood. The "
                "control: it tells the pipeline which DNA differences are inherited "
                "rather than newly arisen in the tumor.",
        "how": "Supplied externally (stage 0). A pipeline root — not produced by any stage.",
    },
    "tumor_rna": {
        "title": "Tumor RNA — raw reads",
        "format": "FASTQ (typically)",
        "what": "What the tumor is actually transcribing. Used to keep only mutations "
                "in genes the tumor expresses (no RNA → no protein → no target).",
        "how": "Supplied externally (stage 0). A pipeline root — not produced by any stage.",
    },
    "reference": {
        "title": "Reference genome (FASTA)",
        "format": "FASTA (+ .fai index)",
        "what": "The human genome that every read is aligned to and every variant is "
                "called against. Contig naming (chr21 vs 21) must match the BAMs or "
                "coordinate lookups silently miss.",
        "how": "Shared external reference. A pipeline root.",
    },
    "proteome": {
        "title": "Human proteome (FASTA)",
        "format": "FASTA",
        "what": "Every normal human protein sequence. Stage 5 checks each candidate "
                "peptide against it to flag self-peptides (autoimmunity risk).",
        "how": "Shared external reference. A pipeline root.",
    },

    # ---- stage 1: normalized alignments ----
    "tumor_dna_bam": {
        "title": "Tumor DNA — aligned",
        "format": "BAM (coordinate-sorted + .bai)",
        "what": "Tumor DNA reads placed at their genome positions, ready for somatic "
                "variant calling.",
        "how": "Stage 1 (input): bwa-mem align (or just sort/index if the source is "
               "already aligned) → coordinate-sort → index.",
    },
    "normal_dna_bam": {
        "title": "Normal DNA — aligned",
        "format": "BAM (coordinate-sorted + .bai)",
        "what": "Germline DNA reads aligned; the baseline the tumor is subtracted "
                "against so only somatic mutations remain.",
        "how": "Stage 1 (input): bwa-mem align (or sort/index if pre-aligned) → "
               "coordinate-sort → index.",
    },
    "tumor_rna_bam": {
        "title": "Tumor RNA — aligned",
        "format": "BAM (coordinate-sorted + .bai)",
        "what": "Tumor RNA reads aligned so expression can be measured per gene.",
        "how": "Stage 1 (input): STAR splice-aware alignment (introns spliced across, "
               "unlike DNA) → coordinate-sort → index.",
    },

    # ---- stage 2a / 2b ----
    "somatic_vcf": {
        "title": "Somatic variants (annotated VCF)",
        "format": "VCF with VEP CSQ annotation",
        "what": "The tumor-specific mutations (present in tumor DNA, absent in normal), "
                "each annotated with gene, protein change, and the wild-type protein "
                "sequence — everything stage 3 needs to build mutant peptides.",
        "how": "Stage 2a (variants): Mutect2 calls tumor-vs-normal → FilterMutectCalls "
               "→ VEP --plugin Wildtype writes SYMBOL / Amino_acids / Protein_position / "
               "WildtypeProtein into the CSQ field.",
    },
    "hla_json": {
        "title": "HLA genotype (JSON)",
        "format": "JSON { sample_id, alleles[], source }",
        "what": "The patient's MHC class-I alleles (HLA-A/B/C). These molecules present "
                "peptides to T cells, so they decide which neoantigens are even visible "
                "to the immune system.",
        "how": "Stage 2b (hla): the default typer looks up the published germline "
               "genotype by sample_id (no reads); OptiTypeTyper instead types it from "
               "normal_dna.bam.",
    },

    # ---- stage 3 → 6 ----
    "candidates_tsv": {
        "title": "Neoantigen candidates (TSV)",
        "format": "TSV, one row per mutant peptide window",
        "what": "Short mutant peptide windows tiled across each expressed mutation — "
                "the raw list of things that might be neoantigens, each with provenance "
                "back to its mutation.",
        "how": "Stage 3 (candidates): read the annotated VCF, slide a window around each "
               "mutated residue using VEP's WildtypeProtein, and drop mutations in "
               "genes with no RNA expression.",
    },
    "ranked_tsv": {
        "title": "Ranked candidates (TSV)",
        "format": "TSV = candidates + score columns",
        "what": "The candidate peptides scored and ordered for the patient's own HLA "
                "alleles — best-first. Carries a presentation score (will it be "
                "displayed?), agretopicity + dissimilarity-to-self (will a T cell "
                "react?), and a tier label; gated-out peptides are flagged, not dropped.",
        "how": "Stage 4 (rank): the default ranker GATES on MHCflurry presentation + "
               "expression, then ranks survivors by the Luksza quality composite "
               "(agretopicity × dissimilarity-to-self). Presentation is conditioned "
               "first because recognition features are meaningless on un-presented "
               "peptides (TESLA). Pluggable — see docs/ranking_methodology.md.",
    },
    "filtered_tsv": {
        "title": "Filtered candidates (TSV)",
        "format": "TSV = ranked + pass/fail flag columns",
        "what": "Ranked peptides with safety/practicality verdicts attached: autoimmunity "
                "(exact proteome match), clonality (CCF), manufacturability. It flags "
                "rows; it does not drop them.",
        "how": "Stage 5 (eval): three rule-based filters add flag columns. The survivors "
               "are what stage 6 is allowed to build from.",
    },
    "construct_fasta": {
        "title": "Vaccine construct (FASTA)",
        "format": "FASTA — amino-acid + nucleotide records",
        "what": "The final designed vaccine: the top surviving peptides strung together "
                "with linkers (amino-acid record), plus a codon-optimized DNA ORF that "
                "encodes it (nucleotide record).",
        "how": "Stage 6 (construct): survivor gate → AAY-linked polypeptide → "
               "reverse-translate to codon-optimized nucleotides.",
    },
    "construct_json": {
        "title": "Construct recipe (JSON)",
        "format": "JSON",
        "what": "A reproducible record of how the construct was assembled — peptides used, "
                "linker, codon table, and any MVP omissions — so the design can be "
                "regenerated and audited.",
        "how": "Stage 6 (construct): written alongside construct.fasta.",
    },
}


def build_file_docs(case) -> dict[str, dict[str, str]]:
    """Resolve FILE_DOCS (keyed by Case logical name) to a `{basename: doc}` map for
    a concrete Case, so viz can look docs up by the filenames it sees in the graph.

    Handles external roots (whose basenames vary by data source) correctly, because
    the Case knows their real paths. A doc carries its `logical` name for reference.
    """
    out: dict[str, dict[str, str]] = {}
    for logical, doc in FILE_DOCS.items():
        path = getattr(case, logical, None)
        if path is None:
            continue
        out[path.name] = {**doc, "logical": logical}
    return out
