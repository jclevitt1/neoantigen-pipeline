"""mutect2_vep — stage 2a default source: Mutect2 call + VEP annotate (deferred)."""
from .caller import Mutect2VepCaller, COMMAND_PLAN

__all__ = ["Mutect2VepCaller", "COMMAND_PLAN"]
