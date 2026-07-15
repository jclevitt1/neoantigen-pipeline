"""
curated.py — a CURATED panel of REAL oncogenic hotspot neoantigens; a superset of
the single-variant DEMO_VARIANTS. It drives the Option-A COMPONENT TEST: exercising
stages 3->6 (windows -> MHCflurry presentation gate -> Luksza composite -> construct)
on biologically real peptides, in isolation from the genomics front end.

HONESTY CONTRACT (same spirit as source.py's FixtureVariants):
    These are REAL missense mutations on REAL human wild-type proteins, but this
    module asserts NOTHING about whether any given tumour actually carries them. It
    is a wiring/science test for the ranker, not a measurement. The "present in the
    sample" claim is deliberately omitted -- asserting it would fabricate data.

WHY IT'S TRUSTWORTHY:
    The wild-type protein for each variant is fetched live from UniProt and VERIFIED
    before use: build_curated_records() asserts  wildtype[protein_position-1] == ref_aa
    and raises otherwise, so a mis-indexed or wrong sequence fails LOUDLY instead of
    silently producing the wrong peptide. (This guard is not paranoia: during
    authoring, a naive position lookup mis-counted a wrapped FASTA and "confirmed" a
    residue that was actually wrong. Never trust an unverified sequence window.)

FIELD SCOPE:
    Only protein-level fields drive stage 3 (wildtype / protein_position / ref_aa /
    alt_aa / gene / transcript / vaf). Genomic chrom/pos/ref/alt are pass-through
    metadata; real values are filled only where verified (KRAS, from the SEQC2 fixture
    locus) and otherwise pos=0 with the true chromosome -- we don't invent coordinates.
    vaf is blank (no measured allele fraction to claim). Transcripts are MANE Select.

HLA:
    DEMO_HLA_PANEL is a set of common, MHCflurry-supported class-I alleles that
    includes the published restricting alleles for the shared neoantigens below, so
    the presentation gate is biologically meaningful. Wire it into the Case via
        KnownGenotypeTyper(table={case.sample_id: DEMO_HLA_PANEL})
"""
from __future__ import annotations

import urllib.request

from ..base import VariantRecord

_UNIPROT_FASTA = "https://rest.uniprot.org/uniprotkb/{acc}.fasta"

# Common class-I alleles, all MHCflurry-supported. Includes the published
# restrictions for the hotspots below: C*08:02 (KRAS G12D), A*11:01 (KRAS G12V),
# A*02:01 (TP53 R175H).
DEMO_HLA_PANEL = [
    "HLA-A*02:01", "HLA-A*01:01", "HLA-A*03:01", "HLA-A*11:01", "HLA-A*24:02",
    "HLA-B*07:02", "HLA-B*08:01", "HLA-C*07:01", "HLA-C*08:02",
]

# Curated real missense hotspots. `uniprot` supplies the WT sequence (fetched +
# verified); `transcript` is the MANE Select Ensembl transcript. Published
# restriction / immunogenicity references are noted per entry.
CURATED_HOTSPOTS = [
    # KRAS G12D -- shared driver; TIL therapy against G12D on HLA-C*08:02
    #   (Tran et al., NEJM 2016, PMID 27959684). Genomic locus from the SEQC2 fixture.
    dict(gene="KRAS", uniprot="P01116", transcript="ENST00000311936",
         protein_position=12, ref_aa="G", alt_aa="D",
         chrom="chr12", pos=25245350, ref="C", alt="T"),
    # KRAS G12V -- shared driver; reactive T cells restricted by HLA-A*11:01
    #   (Tran et al., Science 2015, PMID 24812403). Same codon-12 locus.
    dict(gene="KRAS", uniprot="P01116", transcript="ENST00000311936",
         protein_position=12, ref_aa="G", alt_aa="V",
         chrom="chr12", pos=25245350, ref="C", alt="A"),
    # BRAF V600E -- canonical melanoma / CRC driver.
    dict(gene="BRAF", uniprot="P15056", transcript="ENST00000646891",
         protein_position=600, ref_aa="V", alt_aa="E",
         chrom="chr7", pos=0, ref="", alt=""),
    # TP53 R175H -- hotspot; HLA-A*02:01-restricted TCRs isolated
    #   (Malekzadeh et al., J Clin Invest 2019, PMID 30829653).
    dict(gene="TP53", uniprot="P04637", transcript="ENST00000269305",
         protein_position=175, ref_aa="R", alt_aa="H",
         chrom="chr17", pos=0, ref="", alt=""),
    # PIK3CA H1047R -- common activating hotspot.
    dict(gene="PIK3CA", uniprot="P42336", transcript="ENST00000263967",
         protein_position=1047, ref_aa="H", alt_aa="R",
         chrom="chr3", pos=0, ref="", alt=""),
    # EGFR L858R -- NSCLC driver.
    dict(gene="EGFR", uniprot="P00533", transcript="ENST00000275493",
         protein_position=858, ref_aa="L", alt_aa="R",
         chrom="chr7", pos=0, ref="", alt=""),
]


def _fetch_wildtype(acc: str) -> str:
    """Fetch a UniProt canonical protein sequence (residues only)."""
    raw = urllib.request.urlopen(_UNIPROT_FASTA.format(acc=acc), timeout=30).read().decode()
    return "".join(line.strip() for line in raw.splitlines() if not line.startswith(">"))


def build_curated_records(hotspots=None, fetch=_fetch_wildtype) -> list[VariantRecord]:
    """Build VariantRecords for the curated panel, fetching + VERIFYING each WT.

    Raises ValueError if a fetched sequence's residue at `protein_position` is not
    the stated `ref_aa` -- refusing to emit a wrong peptide. `fetch` is injectable
    (accepts a UniProt accession, returns the sequence) for offline testing.
    """
    out: list[VariantRecord] = []
    for h in (hotspots or CURATED_HOTSPOTS):
        wt = fetch(h["uniprot"])
        pp = h["protein_position"]
        if not (0 < pp <= len(wt)):
            raise ValueError(
                f"{h['gene']}: protein_position {pp} out of range (seq len {len(wt)})"
            )
        anchor = wt[pp - 1]
        if anchor != h["ref_aa"]:
            raise ValueError(
                f"{h['gene']} {h['ref_aa']}{pp}{h['alt_aa']}: UniProt {h['uniprot']} "
                f"has {anchor!r} at position {pp}, not {h['ref_aa']!r}. Refusing to "
                f"build a wrong peptide -- check the accession/position."
            )
        out.append(VariantRecord(
            chrom=h["chrom"], pos=h["pos"], ref=h["ref"], alt=h["alt"],
            gene=h["gene"], transcript=h["transcript"],
            ref_aa=h["ref_aa"], alt_aa=h["alt_aa"], protein_position=pp,
            wildtype=wt, consequence="missense_variant", vaf="",
        ))
    return out
