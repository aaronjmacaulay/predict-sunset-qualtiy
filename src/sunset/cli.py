"""
cli.py — command-line interface: argument parsing and text formatting only.

  sunset score <lat> <lon> [YYYY-MM-DD]     live score for a place (needs network)
  sunset scenarios                          worked example + the 9 documented scenarios
  sunset terrain <lat> <lon> <azimuth>      horizon scan on its own (needs network)
"""

import argparse
import sys

from sunset import scoring, terrain
from sunset.models import MissingDataError, Observation, ScoreResult
from sunset.pinpoint import PinpointResult, pinpoint
from sunset.sources.openmeteo import OpenMeteo


def _num(x) -> str:
    """Print API numbers the way they arrive: 40.0 -> '40', 47.5 -> '47.5'."""
    return str(int(x)) if isinstance(x, float) and x.is_integer() else str(x)


def format_trace(o: Observation, r: ScoreResult) -> str:
    return "\n".join([
        f"  TERM 1  light path gate           = {r.gate:.3f}",
        f"            upwind low cloud {o.cloud_low_upwind:>5.0f}%  -> path    {r.path:.3f}",
        f"            terrain block   {o.terrain_block_deg:>5.1f}deg -> terrain {r.terrain:.3f}",
        f"  TERM 2  canvas                    = {r.canvas:.3f}",
        f"            high cloud      {o.cloud_high:>5.0f}%  -> bell    {r.high:.3f}  (x0.70)",
        f"            mid cloud       {o.cloud_mid:>5.0f}%  -> bell    {r.mid:.3f}  (x0.30)",
        f"  TERM 3  clarity                   = {r.clarity:.3f}",
        f"            RH              {o.rh_2m:>5.0f}%  -> {r.rh_f:.3f} ^0.5",
        f"            visibility   {o.visibility_m:>8.0f}m  -> {r.vis_f:.3f} ^0.6",
        f"            PBL height   {o.pbl_height_m:>8.0f}m  -> {r.pbl_f:.3f}",
        f"  TERM 4  aerosol multiplier        = {r.aerosol:.3f}",
        f"            AOD            {o.aod:>6.2f}   -> boost   {r.boost:.3f}",
        f"            overload factor           {r.overload:.3f}",
        f"            PM2.5          {o.pm25:>6.1f}   -> {r.pm_pen:.3f}",
        f"  ----------------------------------------------------",
        f"  {r.gate:.3f} x {r.canvas:.3f} x {r.clarity:.3f} x {r.aerosol:.3f} = {r.raw:.4f}",
        f"  SCORE = {r.score}/100   ({r.label})",
    ])


def format_scenarios() -> str:
    worked = scoring.SCENARIOS["Post-frontal classic"]
    lines = ["=" * 60, "WORKED EXAMPLE — 'Post-frontal classic'", "=" * 60,
             format_trace(worked, scoring.score(worked)),
             "", "=" * 60, "ALL SCENARIOS", "=" * 60]
    for name, obs in scoring.SCENARIOS.items():
        s = scoring.score(obs).score
        lines.append(f"{name:<34} {s:>3}/100  {'#' * int(s / 2.5)} {scoring.label(s)}")
    return "\n".join(lines)


def format_pinpoint(p: PinpointResult) -> str:
    lines = [
        f"Pinpoint sunset score — ({_num(p.lat)}, {_num(p.lon)}) on {p.date}",
        "=" * 60,
        f"Sunset time: {p.sunset_local} ({p.timezone})",
        f"Solar azimuth at sunset: {p.azimuth_deg:.1f} deg",
        f"Evaluated hour (nearest bucket): {p.evaluated_hour}",
        "Upwind low cloud samples:",
    ]
    for u in p.upwind:
        lines.append(f"  {u.km}km @ {p.azimuth_deg:.0f}deg -> ({u.lat:.3f}, {u.lon:.3f}): {_num(u.low_cloud)}%")
    lines += [
        f"Worst-case upwind low cloud: {_num(p.observation.cloud_low_upwind)}%",
        f"Observer elevation: {_num(p.terrain.observer_elevation_m)}m",
        "Terrain horizon scan:",
    ]
    for b in p.terrain.bearings:
        lines.append(f"  {b.bearing:.1f}deg -> block {b.block_deg:.2f}deg")
    lines += [
        f"terrain_block_deg (max across bearings): {p.terrain.terrain_block_deg:.2f}",
        "",
        format_trace(p.observation, p.result),
    ]
    return "\n".join(lines)


def format_terrain(t: terrain.TerrainResult) -> str:
    lines = [f"Observer elevation: {_num(t.observer_elevation_m)}m"]
    for b in t.bearings:
        lines.append(f"Bearing {b.bearing:.1f}deg -> block {b.block_deg:.2f}deg")
        for s in b.samples:
            lines.append(f"    {s.km:>3}km  elev {_num(s.elevation_m):>5}m  angle {s.angle_deg:.2f}deg")
    lines.append(f"\nterrain_block_deg (max across bearings) = {t.terrain_block_deg:.2f}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sunset", description="Hyperlocal sunset quality predictor")
    sub = parser.add_subparsers(dest="command", required=True)

    p_score = sub.add_parser("score", help="live score for a place and date")
    p_score.add_argument("lat", type=float)
    p_score.add_argument("lon", type=float)
    p_score.add_argument("date", nargs="?", help="YYYY-MM-DD (default: today at that location)")

    sub.add_parser("scenarios", help="worked example and the documented scenarios")

    p_terrain = sub.add_parser("terrain", help="horizon scan toward a given azimuth")
    p_terrain.add_argument("lat", type=float)
    p_terrain.add_argument("lon", type=float)
    p_terrain.add_argument("azimuth", type=float, help="sunset azimuth, degrees")

    args = parser.parse_args(argv)
    try:
        if args.command == "score":
            print(format_pinpoint(pinpoint(args.lat, args.lon, args.date)))
        elif args.command == "scenarios":
            print(format_scenarios())
        elif args.command == "terrain":
            points = terrain.profile_points(args.lat, args.lon, args.azimuth)
            print(format_terrain(terrain.horizon_profile(args.azimuth, OpenMeteo().elevations(points))))
    except (MissingDataError, RuntimeError, OSError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
