"""
models.py — the data contracts shared by every layer (see ARCHITECTURE.md).

No imports from the rest of the package: everything else depends on this
module, never the other way round.
"""

import math
from dataclasses import dataclass, fields


class MissingDataError(ValueError):
    """An input the scorer needs is missing or not a number.

    Raised instead of letting a None/NaN from an API flow through the maths
    and silently produce a meaningless score (ARCHITECTURE.md S5).
    """


@dataclass(frozen=True)
class Observation:
    """Everything the scorer needs, at sunset, for one place."""

    cloud_high: float          # % high cloud at the spot
    cloud_mid: float           # % mid cloud at the spot
    cloud_low_upwind: float    # % low cloud toward the sun (worst of 50/150/250 km)
    rh_2m: float               # % relative humidity at 2 m
    visibility_m: float        # m
    pbl_height_m: float        # m, boundary layer height
    aod: float                 # aerosol optical depth (unitless)
    pm25: float                # µg/m³
    terrain_block_deg: float   # degrees the real horizon sits above flat

    def __post_init__(self):
        bad = [f.name for f in fields(self)
               if not isinstance(getattr(self, f.name), (int, float))
               or isinstance(getattr(self, f.name), bool)
               or not math.isfinite(getattr(self, f.name))]
        if bad:
            raise MissingDataError(f"Observation has missing or non-numeric values: {', '.join(bad)}")


@dataclass(frozen=True)
class ScoreResult:
    """The scorer's output: the score plus every term and sub-factor.

    The terms and sub-factors are the features a personalised score would
    weight (NEXT-STEPS F2).
    """

    score: int                 # 0-100
    label: str                 # "poor" ... "exceptional"
    raw: float                 # gate * canvas * clarity * aerosol, before rounding

    # TERM 1 — light path gate, and its sub-factors
    gate: float
    path: float
    terrain: float
    # TERM 2 — canvas
    canvas: float
    high: float
    mid: float
    # TERM 3 — clarity
    clarity: float
    rh_f: float
    vis_f: float
    pbl_f: float
    # TERM 4 — aerosol
    aerosol: float
    boost: float
    overload: float
    pm_pen: float
