"""
sunset_score.py — a worked sunset-quality scoring model.

FROZEN REFERENCE COPY as of 2026-09-04. sunset_score.js is the actively
maintained implementation (used by pinpoint.js and terrain.js) - edit that
one going forward, not this file. Kept here as the original documented
formula this project started from.

Structure is MULTIPLICATIVE, not a weighted average. That is the key modelling
decision: a sunset is a chain of necessary conditions, and any single broken
link ruins it. Light must (1) reach the cloud deck, (2) find a deck worth
lighting, (3) travel through clean enough air, (4) get its colour saturated by
the right amount of aerosol. Averaging would let a perfect cirrus deck paper
over a solid marine layer that is physically blocking the sun.

Inputs map 1:1 onto the free Open-Meteo endpoints (see README section at bottom).
"""

import math

# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def bell(x, mu, sigma):
    """Peaked response: 1.0 at the optimum, falling off either side.
    Used wherever 'more' is not monotonically better — cloud cover and aerosol
    both have a sweet spot with too-little and too-much failing differently."""
    return math.exp(-((x - mu) ** 2) / (2 * sigma ** 2))


# ----------------------------------------------------------------------------
# the four terms
# ----------------------------------------------------------------------------

def light_path_gate(cloud_low_upwind, terrain_block_deg):
    """TERM 1 — can the light physically get through?

    Note this uses UPWIND low cloud (sampled along the solar azimuth, 50-250 km
    west), not low cloud overhead. Light reaching the cirrus above you left the
    sun and travelled west-to-east; what matters is the deck it passed through
    on the way, not the deck over your head.

    Terrain never fully kills the score: high cirrus is lit from far beyond the
    ridge, so a blocked horizon costs you the low-angle reddest light but not
    the whole show. Hence the 0.25 floor.
    """
    path = 1.0 - (clamp(cloud_low_upwind, 0, 100) / 100.0) ** 1.5
    terrain = clamp(1.0 - terrain_block_deg / 8.0, 0.25, 1.0)
    return path * terrain, path, terrain


def canvas(cloud_high, cloud_mid):
    """TERM 2 — is there anything up there to light up?

    Peaked at ~55% high cloud. Zero cloud means an empty sky with nothing to
    catch colour; 100% means a solid deck that goes flat grey because no light
    gets underneath it. Mid cloud contributes at lower weight and a lower
    optimum, since it blocks as readily as it reflects.
    """
    high = bell(cloud_high, mu=55, sigma=28)
    mid = bell(cloud_mid, mu=30, sigma=25)
    return clamp(0.70 * high + 0.30 * mid, 0.0, 1.0), high, mid


def clarity(rh_2m, visibility_m, pbl_height_m):
    """TERM 3 — will the colour arrive saturated or washed out?

    Fractional exponents deliberately soften each sub-factor so no single one
    dominates; these are correlated measurements of the same physical thing
    (near-surface scattering), so full multiplication would double-count.
    """
    rh_f = clamp(1.0 - (rh_2m - 45.0) / 55.0, 0.25, 1.0)
    vis_f = clamp(visibility_m / 24000.0, 0.20, 1.0)
    pbl_f = clamp(0.55 + (pbl_height_m / 2000.0) * 0.45, 0.55, 1.0)
    return (rh_f ** 0.5) * (vis_f ** 0.6) * pbl_f, rh_f, vis_f, pbl_f


def aerosol(aod, pm25):
    """TERM 4 — the colour-saturation multiplier. The only term that can
    exceed 1.0, because moderate particulate genuinely IMPROVES a sunset by
    scattering blue out of the path. Peaked at AOD ~0.18; beyond 0.5 the sky
    starts going flat brown and the extra penalty kicks in.
    """
    boost = 0.85 + 0.35 * bell(aod, mu=0.18, sigma=0.12)
    overload = clamp(1.0 - (aod - 0.5) / 0.8, 0.35, 1.0) if aod > 0.5 else 1.0
    pm_pen = clamp(1.0 - max(0.0, pm25 - 20.0) / 60.0, 0.5, 1.0)
    return boost * overload * pm_pen, boost, overload, pm_pen


# ----------------------------------------------------------------------------
# top level
# ----------------------------------------------------------------------------

def score(o, trace=False):
    gate, path, terr = light_path_gate(o["cloud_low_upwind"], o["terrain_block_deg"])
    canv, c_hi, c_mid = canvas(o["cloud_high"], o["cloud_mid"])
    clar, rh_f, vis_f, pbl_f = clarity(o["rh_2m"], o["visibility_m"], o["pbl_height_m"])
    aer, boost, overload, pm_pen = aerosol(o["aod"], o["pm25"])

    raw = gate * canv * clar * aer
    final = clamp(round(raw * 100), 0, 100)

    if trace:
        print(f"  TERM 1  light path gate           = {gate:.3f}")
        print(f"            upwind low cloud {o['cloud_low_upwind']:>5.0f}%  -> path    {path:.3f}")
        print(f"            terrain block   {o['terrain_block_deg']:>5.1f}deg -> terrain {terr:.3f}")
        print(f"  TERM 2  canvas                    = {canv:.3f}")
        print(f"            high cloud      {o['cloud_high']:>5.0f}%  -> bell    {c_hi:.3f}  (x0.70)")
        print(f"            mid cloud       {o['cloud_mid']:>5.0f}%  -> bell    {c_mid:.3f}  (x0.30)")
        print(f"  TERM 3  clarity                   = {clar:.3f}")
        print(f"            RH              {o['rh_2m']:>5.0f}%  -> {rh_f:.3f} ^0.5")
        print(f"            visibility   {o['visibility_m']:>8.0f}m  -> {vis_f:.3f} ^0.6")
        print(f"            PBL height   {o['pbl_height_m']:>8.0f}m  -> {pbl_f:.3f}")
        print(f"  TERM 4  aerosol multiplier        = {aer:.3f}")
        print(f"            AOD            {o['aod']:>6.2f}   -> boost   {boost:.3f}")
        print(f"            overload factor           {overload:.3f}")
        print(f"            PM2.5          {o['pm25']:>6.1f}   -> {pm_pen:.3f}")
        print(f"  ----------------------------------------------------")
        print(f"  {gate:.3f} x {canv:.3f} x {clar:.3f} x {aer:.3f} = {raw:.4f}")
        print(f"  SCORE = {final}/100   ({label(final)})")

    return final


def label(s):
    if s >= 75: return "exceptional"
    if s >= 55: return "very good"
    if s >= 35: return "decent"
    if s >= 18: return "mediocre"
    return "poor"


# ----------------------------------------------------------------------------
# scenarios
# ----------------------------------------------------------------------------

SCENARIOS = {
    "Post-frontal classic": dict(
        cloud_high=60, cloud_mid=25, cloud_low_upwind=10, rh_2m=48,
        visibility_m=24000, pbl_height_m=1400, aod=0.16, pm25=7,
        terrain_block_deg=0.5),

    "Marine layer (coastal summer)": dict(
        cloud_high=55, cloud_mid=20, cloud_low_upwind=85, rh_2m=88,
        visibility_m=9000, pbl_height_m=350, aod=0.10, pm25=6,
        terrain_block_deg=0.5),

    "Wildfire smoke, moderate": dict(
        cloud_high=35, cloud_mid=15, cloud_low_upwind=5, rh_2m=40,
        visibility_m=14000, pbl_height_m=1600, aod=0.42, pm25=38,
        terrain_block_deg=0.5),

    "Wildfire smoke, heavy": dict(
        cloud_high=30, cloud_mid=10, cloud_low_upwind=5, rh_2m=38,
        visibility_m=4000, pbl_height_m=1500, aod=1.30, pm25=145,
        terrain_block_deg=0.5),

    # --- contrast pair: IDENTICAL sky overhead, only upwind low cloud differs.
    # This is the whole argument for sampling along the solar azimuth.
    "Pair A: clear to the west": dict(
        cloud_high=55, cloud_mid=20, cloud_low_upwind=5, rh_2m=55,
        visibility_m=20000, pbl_height_m=1200, aod=0.18, pm25=10,
        terrain_block_deg=0.5),

    "Pair B: same sky, deck 120km west": dict(
        cloud_high=55, cloud_mid=20, cloud_low_upwind=75, rh_2m=55,
        visibility_m=20000, pbl_height_m=1200, aod=0.18, pm25=10,
        terrain_block_deg=0.5),

    "Bluebird clear sky": dict(
        cloud_high=0, cloud_mid=0, cloud_low_upwind=0, rh_2m=45,
        visibility_m=24000, pbl_height_m=1800, aod=0.09, pm25=4,
        terrain_block_deg=0.5),

    "Solid overcast": dict(
        cloud_high=100, cloud_mid=95, cloud_low_upwind=95, rh_2m=92,
        visibility_m=7000, pbl_height_m=500, aod=0.12, pm25=9,
        terrain_block_deg=0.5),

    "Ideal sky, but ridge to the west": dict(
        cloud_high=60, cloud_mid=25, cloud_low_upwind=10, rh_2m=48,
        visibility_m=24000, pbl_height_m=1400, aod=0.16, pm25=7,
        terrain_block_deg=6.0),
}


if __name__ == "__main__":
    print("=" * 60)
    print("WORKED EXAMPLE — 'Post-frontal classic'")
    print("=" * 60)
    score(SCENARIOS["Post-frontal classic"], trace=True)

    print()
    print("=" * 60)
    print("ALL SCENARIOS")
    print("=" * 60)
    for name, obs in SCENARIOS.items():
        s = score(obs)
        bar = "#" * int(s / 2.5)
        print(f"{name:<34} {s:>3}/100  {bar} {label(s)}")
