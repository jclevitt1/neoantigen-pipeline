"""
caller.py — the DEFAULT stage-2a source: GATK Mutect2 (call) + Ensembl VEP
(annotate). This is the honest scientific path; its execution defers to Colab
because it needs the aligned BAMs, the reference genome, and the VEP cache +
Wildtype-protein plugin — none of which belong on a laptop in Da Nang.

We build the *contract* (inputs it declares, output format via write_annotated_vcf)
and document the exact command plan, so the Colab run is a transcription, not a
redesign. `produce()` raises until wired — nothing downstream fabricates a call.
"""
from __future__ import annotations

from ..base import VariantSource
from ... import checks

# The command plan a Colab cell transcribes. Kept as documentation next to the
# code that will run it, so the biology and the invocation don't drift apart.
COMMAND_PLAN = """\
# 1. Call somatic variants, tumor with matched normal (germline subtracted):
gatk Mutect2 -R {reference} \\
     -I {tumor_bam} -tumor {tumor_sample} \\
     -I {normal_bam} -normal {normal_sample} \\
     -O {raw_vcf}
# 2. Flag low-confidence calls:
gatk FilterMutectCalls -R {reference} -V {raw_vcf} -O {filtered_vcf}
# 3. Annotate protein consequence + attach the WILDTYPE PROTEIN stage 3 needs:
vep -i {filtered_vcf} -o {annotated_vcf} --vcf \\
    --symbol --transcript_version --hgvs \\
    --plugin Wildtype \\
    --fasta {reference} --cache --offline
# (--plugin Wildtype is what pVACseq relies on to put WildtypeProtein in the CSQ.)
"""


class Mutect2VepCaller(VariantSource):
    """Real somatic calling + annotation. Deferred to Colab (see COMMAND_PLAN)."""

    def required_inputs(self, case) -> list:
        # the real DAG edges for 2a: two BAMs and the reference genome
        return [case.tumor_dna_bam, case.normal_dna_bam, case.reference]

    def dry_check(self, case) -> None:
        checks.require_bgzf(case.tumor_dna_bam)
        checks.require_bgzf(case.normal_dna_bam)
        checks.require_nonempty(case.reference)

    def produce(self, case, out_path) -> None:
        raise NotImplementedError(
            "Mutect2VepCaller.produce — run in Colab; see COMMAND_PLAN. "
            "For a tool-free wiring/demo run, pass FixtureVariants() as the source."
        )
