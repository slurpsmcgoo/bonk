#!/usr/bin/env python3
"""
Race day planner for ultra-endurance events.

Generates best / expected / worst case aid-station splits, nutrition
requirements, and hydration needs using the bonk physics model.

Usage:
    python plan.py <gpx> <aid_stations.json> <athlete.json> [options]

    python plan.py "2026 Huron 100.gpx" huron100_2026_aid_stations.json athlete.json

Options:
    --mass FLOAT        Body mass kg (overrides athlete.json default 65)
    --glucose FLOAT     External carb intake g/hr (default 60)
    --bag-size FLOAT    Grams per nutrition bag (default from aid station JSON or 95)
    --output PATH       Base path for output files (default: race name stem)
    --no-excel          Skip Excel output
    --no-plot           Skip plot output
"""

import argparse
import datetime
import json
import math
import os
import sys
import time
import urllib.request


# ── Console tee (stdout → screen + file) ────────────────────────────────────

class _Tee:
    """Mirror stdout to a file and the terminal simultaneously."""
    def __init__(self, filepath: str):
        self._file   = open(filepath, 'w')
        self._stdout = sys.stdout
        sys.stdout   = self

    def write(self, data: str):
        self._stdout.write(data)
        self._file.write(data)

    def flush(self):
        self._stdout.flush()
        self._file.flush()

    def close(self):
        sys.stdout = self._stdout
        self._file.close()

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'source'))
import bonk

# ── Constants ────────────────────────────────────────────────────────────────

# Carbohydrate utilization vs % VO2max (from Utilities sheet)
_CARB_VO2_PCT  = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
_CARB_CARB_PCT = [0, 1,  2,  4,  6, 13, 16, 20, 25, 31, 37, 43, 48, 55, 62, 68, 74, 72, 82, 88,  94]

METABOLIC_EFFICIENCY = 0.25   # mechanical → metabolic
KCAL_PER_GRAM_CARB   = 4.0
KCAL_PER_JOULE       = 1.0 / 4184.0


# ── Physiology helpers ───────────────────────────────────────────────────────

def carb_fraction(vo2_pct: float) -> float:
    """Fraction of metabolic energy from carbohydrates at a given % VO2max."""
    return float(np.interp(vo2_pct, _CARB_VO2_PCT, _CARB_CARB_PCT)) / 100.0


def wet_bulb_temp(temp_c: float, dew_point_c: float) -> float:
    """Wet-bulb temperature approximation from dry-bulb and dew-point (°C)."""
    return temp_c - (temp_c - dew_point_c) * 0.7


def sweat_rate_l_hr(wet_bulb_c: float, vo2_pct: float) -> float:
    """Sweat rate in L/hr as a function of wet-bulb temperature and intensity."""
    return (414.0 + 11.45 * wet_bulb_c + 2.6 * vo2_pct) / 1000.0


# ── Weather ──────────────────────────────────────────────────────────────────

def _fetch_openmeteo(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat:.4f}&longitude={lon:.4f}"
        f"&hourly=temperature_2m,relative_humidity_2m,cloud_cover,dew_point_2m"
        f"&timezone=auto"
        f"&start_date={start_date}&end_date={end_date}"
    )
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read())


def load_weather(lat: float, lon: float, start_dt: datetime.datetime,
                 max_duration_h: float, cache_path: str) -> dict | None:
    """Return hourly weather dict, using cache if < 1 day old."""
    end_dt    = start_dt + datetime.timedelta(hours=max_duration_h + 2)
    start_str = start_dt.date().isoformat()
    end_str   = end_dt.date().isoformat()

    if os.path.exists(cache_path):
        age_s = time.time() - os.path.getmtime(cache_path)
        if age_s < 86400:
            with open(cache_path) as f:
                data = json.load(f)
            print(f"  Weather: loaded from cache ({age_s / 3600:.1f}h old)")
            return data

    print("  Weather: fetching from Open-Meteo…")
    try:
        data = _fetch_openmeteo(lat, lon, start_str, end_str)
        with open(cache_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"  Weather: cached to {cache_path}")
        return data
    except Exception as e:
        print(f"  Weather: fetch failed ({e}) — using defaults")
        return None


def weather_at(data: dict, dt: datetime.datetime) -> dict:
    """Return interpolated weather variables at the given datetime."""
    defaults = {'temperature_2m': 15.0, 'dew_point_2m': 10.0,
                'relative_humidity_2m': 70.0, 'cloud_cover': 50.0}
    if data is None:
        return defaults

    times = data['hourly']['time']       # "2026-06-06T09:00"
    target = dt.strftime('%Y-%m-%dT%H:%M')

    # Find bracketing indices
    idx = 0
    for i, t in enumerate(times):
        if t <= target:
            idx = i

    out = {}
    for key, default in defaults.items():
        vals = data['hourly'].get(key)
        if not vals:
            out[key] = default
            continue
        if idx + 1 < len(vals):
            frac = dt.minute / 60.0
            out[key] = vals[idx] * (1 - frac) + vals[idx + 1] * frac
        else:
            out[key] = vals[idx]
    return out


def average_weather(data: dict, start_dt: datetime.datetime,
                    end_dt: datetime.datetime) -> dict:
    """Average weather variables over a time window."""
    if data is None:
        return {'temperature_2m': 15.0, 'dew_point_2m': 10.0,
                'relative_humidity_2m': 70.0, 'cloud_cover': 50.0}
    keys = ['temperature_2m', 'dew_point_2m', 'relative_humidity_2m', 'cloud_cover']
    times = data['hourly']['time']
    buckets = {k: [] for k in keys}
    for i, t in enumerate(times):
        if start_dt.strftime('%Y-%m-%dT%H:%M') <= t <= end_dt.strftime('%Y-%m-%dT%H:%M'):
            for k in keys:
                if data['hourly'].get(k) and data['hourly'][k][i] is not None:
                    buckets[k].append(data['hourly'][k][i])
    return {k: (sum(v) / len(v) if v else 15.0) for k, v in buckets.items()}


# ── Course helpers ───────────────────────────────────────────────────────────

def gpx_cumulative_distances(gpx_path: str):
    """Return (points, cum_dist_m) from a GPX file."""
    import gpxpy
    with open(gpx_path) as f:
        gpx = gpxpy.parse(f)
    pts = [p for t in gpx.tracks for s in t.segments for p in s.points]
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + bonk.haversine(
            pts[i-1].latitude, pts[i-1].longitude,
            pts[i].latitude,   pts[i].longitude))
    return pts, cum


def nearest_gpx_idx(cum_m: list, target_m: float) -> int:
    arr = np.asarray(cum_m)
    return int(np.argmin(np.abs(arr - target_m)))


# ── Scenario runner (time-varying temperature) ───────────────────────────────

def _temp_power_factor(temp_c: float, ref_temp_c: float) -> float:
    """Ratio of sustainable power at temp_c relative to ref_temp_c.

    Derived from PowerDuration's linear temperature penalty: power ∝ 1/(1+tempFrac),
    where tempFrac = |(T+273)/278 - 1|. Returns >1 when temp_c < ref_temp_c (cooler
    than reference → more power available) and <1 when hotter.
    """
    ref_frac = abs((ref_temp_c + 273.0) / 278.0 - 1.0)
    t_frac   = abs((temp_c     + 273.0) / 278.0 - 1.0)
    return (1.0 + ref_frac) / (1.0 + t_frac)


def run_scenario(course, athlete, env, k: float,
                 weather_data: dict, start_dt: datetime.datetime,
                 n_iter: int = 4) -> bonk.Performance:
    """Solve for race performance with iterative time-varying temperature correction.

    Each iteration:
      1. Run getUltraRaceTime with current per-segment power modifiers.
      2. Use resulting segment arrival times to look up forecast temperature.
      3. Recompute per-segment power modifiers as temp_power_factor(T_segment, T_avg).
    Typically converges in 2–3 iterations; 4 is conservative.
    """
    avg_temp  = env.temperature
    n_segs    = len(course.segments)
    power_mods = np.ones(n_segs)
    perf       = bonk.Performance(env, athlete, course)

    for iteration in range(n_iter):
        perf.getUltraRaceTime(k=k, power_modifiers=power_mods)

        # Recompute modifiers from segment arrival temperatures
        elapsed = 0.0
        new_mods = np.empty(n_segs)
        for i, sp in enumerate(perf.segmentPerformances):
            elapsed += sp.duration
            arrival = start_dt + datetime.timedelta(seconds=elapsed)
            T = weather_at(weather_data, arrival)['temperature_2m']
            new_mods[i] = _temp_power_factor(T, avg_temp)

        # Check convergence (max change in any modifier)
        delta = float(np.max(np.abs(new_mods - power_mods)))
        power_mods = new_mods
        if delta < 1e-4:
            # Run one final solve with converged modifiers
            perf.getUltraRaceTime(k=k, power_modifiers=power_mods)
            break

    return perf


# ── Per-station result builder ───────────────────────────────────────────────

def build_station_results(perf: bonk.Performance, stations: list,
                          cum_gpx_m: list, scale: float,
                          start_dt: datetime.datetime,
                          weather_data: dict,
                          vo2max_effective: float,
                          bag_size_g: float) -> list:
    """
    Return a list of dicts, one per aid station, with timing, nutrition,
    hydration, and weather values.
    """
    results = []
    prev_idx   = 0
    crew_carb_accum = 0.0   # carbs since last crew station
    last_crew_name  = stations[0]['name']

    for i, st in enumerate(stations):
        target_m  = st['cumulative_miles'] * 1609.34 * scale
        gpx_idx   = nearest_gpx_idx(cum_gpx_m, target_m)
        gpx_idx   = min(gpx_idx, len(perf.segmentPerformances))

        # Elapsed time at this station (end of segment gpx_idx - 1)
        elapsed_s = perf.durations[gpx_idx - 1] if gpx_idx > 0 else 0.0
        wall_time = start_dt + datetime.timedelta(seconds=elapsed_s)

        # Aggregate stats for the section since the previous station
        sps = perf.segmentPerformances[prev_idx:gpx_idx]
        if sps:
            section_dur_s = sum(sp.duration for sp in sps)
            section_mech_j = sum(sp.power * sp.duration for sp in sps)
            section_dist_m = sum(sp.segment.length for sp in sps)
            avg_power     = section_mech_j / section_dur_s if section_dur_s > 0 else 0.0
            avg_vo2_pct   = avg_power / vo2max_effective * 100.0 if vo2max_effective > 0 else 60.0
            metabolic_kcal = section_mech_j * KCAL_PER_JOULE / METABOLIC_EFFICIENCY
            carb_frac     = carb_fraction(avg_vo2_pct)
            section_carb_g = carb_frac * metabolic_kcal / KCAL_PER_GRAM_CARB
            pace_min_mile = (section_dur_s / 60.0) / (section_dist_m / 1609.34) if section_dist_m > 0 else 0.0
            elev_gain_m   = sum(max(0.0, sp.segment.elevGain) for sp in sps)
            elev_loss_m   = sum(abs(min(0.0, sp.segment.elevGain)) for sp in sps)
        else:
            section_dur_s = section_mech_j = section_dist_m = 0.0
            avg_power = avg_vo2_pct = metabolic_kcal = section_carb_g = pace_min_mile = 0.0
            elev_gain_m = elev_loss_m = 0.0

        # Weather at arrival
        w       = weather_at(weather_data, wall_time)
        temp_c  = w['temperature_2m']
        dew_c   = w['dew_point_2m']
        humidity = w['relative_humidity_2m']
        cloud   = w['cloud_cover']
        wb      = wet_bulb_temp(temp_c, dew_c)
        sr      = sweat_rate_l_hr(wb, avg_vo2_pct)
        water_l = sr * (section_dur_s / 3600.0)

        # Cutoff buffer
        cutoff_h = st.get('cutoff_h')
        cutoff_buffer_h = (cutoff_h - elapsed_s / 3600.0) if cutoff_h else None

        # Crew bag accumulation: track carbs needed since last crew access
        if i > 0:
            crew_carb_accum += section_carb_g
        if st['crew'] and i > 0:
            bags_to_next_crew = math.ceil(crew_carb_accum / bag_size_g) if crew_carb_accum > 0 else 0
            crew_carb_for_section = crew_carb_accum
            crew_carb_accum = 0.0
            last_crew_name = st['name']
        else:
            bags_to_next_crew = None
            crew_carb_for_section = None

        results.append({
            'name':               st['name'],
            'cumulative_miles':   st['cumulative_miles'],
            'drop_bag':           st.get('drop_bag', False),
            'crew':               st.get('crew', False),
            'pacer':              st.get('pacer', False),
            'aid_type':           st.get('aid_type', 'Full'),
            'cutoff_h':           cutoff_h,
            'elapsed_s':          elapsed_s,
            'elapsed_h':          elapsed_s / 3600.0,
            'wall_time':          wall_time,
            'cutoff_buffer_h':    cutoff_buffer_h,
            'section_dur_s':      section_dur_s,
            'section_dist_m':     section_dist_m,
            'pace_min_mile':      pace_min_mile,
            'elev_gain_m':        elev_gain_m,
            'elev_loss_m':        elev_loss_m,
            'avg_power':          avg_power,
            'avg_vo2_pct':        avg_vo2_pct,
            'metabolic_kcal':     metabolic_kcal,
            'section_carb_g':     section_carb_g,
            'crew_carb_g':        crew_carb_for_section,
            'bags_to_next_crew':  bags_to_next_crew,
            'water_l':            water_l,
            'sweat_rate':         sr,
            'temp_c':             temp_c,
            'dew_c':              dew_c,
            'humidity':           humidity,
            'cloud':              cloud,
            'wet_bulb':           wb,
            'gpx_idx':            gpx_idx,
        })

        prev_idx = gpx_idx

    return results


# ── Console output ───────────────────────────────────────────────────────────

def _fmt_elapsed(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h:02d}:{m:02d}"


def _fmt_pace(min_per_mile: float) -> str:
    if min_per_mile <= 0:
        return "  --  "
    m = int(min_per_mile)
    s = int((min_per_mile - m) * 60)
    return f"{m}:{s:02d}"


def _fmt_buffer(h: float | None) -> str:
    if h is None:
        return "  --  "
    sign = "+" if h >= 0 else "-"
    h = abs(h)
    return f"{sign}{int(h):02d}:{int((h % 1)*60):02d}"


def print_scenario_table(label: str, results: list):
    W = 155
    print()
    print("=" * W)
    print(f"  {label}")
    print("=" * W)
    hdr = (f"{'Aid Station':<30} {'Mile':>5} {'Elapsed':>8} {'Wall Time':>9} "
           f"{'Cutoff':>8} {'Pace':>7} {'VO2%':>5} {'Sec Carb':>9} "
           f"{'Crew Bags':>10} {'Water L':>8} {'Temp°C':>7} {'WB°C':>6} "
           f"{'  +Gain':>7} {'  -Loss':>7}  Flags")
    print(hdr)
    print("-" * W)
    for r in results:
        flags = ""
        if r['drop_bag']: flags += "D"
        if r['crew']:     flags += "C"
        if r['pacer']:    flags += "P"
        if r['aid_type'] == 'H2O Only': flags += " H2O"

        bags_str  = f"{r['bags_to_next_crew']} bags" if r['bags_to_next_crew'] is not None else "  --  "
        carb_str  = f"{r['section_carb_g']:.0f}g" if r['section_carb_g'] > 0 else "--"
        water_str = f"{r['water_l']:.2f}" if r['section_dur_s'] > 0 else "--"
        buf_str   = _fmt_buffer(r['cutoff_buffer_h'])
        gain_str  = f"+{r['elev_gain_m']:.0f}m" if r['elev_gain_m'] > 0 else "--"
        loss_str  = f"-{r['elev_loss_m']:.0f}m" if r['elev_loss_m'] > 0 else "--"

        # Flag if close to or over cutoff
        buf_warn = ""
        if r['cutoff_buffer_h'] is not None:
            if r['cutoff_buffer_h'] < 0:
                buf_warn = " !!DNF!!"
            elif r['cutoff_buffer_h'] < 1.0:
                buf_warn = " *TIGHT*"

        print(f"{r['name']:<30} {r['cumulative_miles']:>5.1f} "
              f"{_fmt_elapsed(r['elapsed_s']):>8} "
              f"{r['wall_time'].strftime('%H:%M'):>9} "
              f"{buf_str:>8} "
              f"{_fmt_pace(r['pace_min_mile']):>7} "
              f"{r['avg_vo2_pct']:>5.1f} "
              f"{carb_str:>9} "
              f"{bags_str:>10} "
              f"{water_str:>8} "
              f"{r['temp_c']:>7.1f} "
              f"{r['wet_bulb']:>6.1f} "
              f"{gain_str:>7} "
              f"{loss_str:>7}  "
              f"{flags}{buf_warn}")

    total_carb  = sum(r['section_carb_g']  for r in results)
    total_water = sum(r['water_l']          for r in results)
    total_gain  = sum(r['elev_gain_m']      for r in results)
    total_loss  = sum(r['elev_loss_m']      for r in results)
    finish = results[-1]
    print("-" * W)
    print(f"  Total: {finish['cumulative_miles']:.1f} mi  "
          f"Finish: {_fmt_elapsed(finish['elapsed_s'])}  "
          f"({finish['wall_time'].strftime('%a %H:%M')})  "
          f"Carbs: {total_carb:.0f} g  "
          f"Water: {total_water:.1f} L  "
          f"Elev: +{total_gain:.0f}m / -{total_loss:.0f}m")
    print()


# ── Plots ────────────────────────────────────────────────────────────────────

def make_plots(scenario_results: dict, scenario_configs: dict,
               all_perfs: dict, start_dt: datetime.datetime,
               gpx_cum_m: list, output_path: str):
    """Four-panel figure: splits, pace, VO2%, cumulative carbs."""
    fig = plt.figure(figsize=(16, 12))
    gs  = gridspec.GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)
    ax_dist  = fig.add_subplot(gs[0, 0])
    ax_pace  = fig.add_subplot(gs[0, 1])
    ax_vo2   = fig.add_subplot(gs[1, 0])
    ax_carb  = fig.add_subplot(gs[1, 1])

    gpx_cum_km = np.array(gpx_cum_m) / 1000.0

    for key, cfg in scenario_configs.items():
        color  = cfg['color']
        label  = cfg['label']
        perf   = all_perfs[key]
        res    = scenario_results[key]

        # Distance vs time (all GPX segments)
        t_h  = np.array([0.0] + list(np.array(perf.durations) / 3600.0))
        d_km = np.array([0.0] + list(np.array(perf.distances)  / 1000.0))
        ax_dist.plot(t_h, d_km, color=color, label=label, linewidth=1.5)

        # Station markers on distance-time
        st_t = [r['elapsed_h'] for r in res]
        st_d = [r['cumulative_miles'] * 1.60934 for r in res]
        ax_dist.scatter(st_t, st_d, color=color, s=20, zorder=5)

        # Pace per section (min/mile) vs cumulative distance
        miles = [r['cumulative_miles'] for r in res if r['pace_min_mile'] > 0]
        paces = [r['pace_min_mile']   for r in res if r['pace_min_mile'] > 0]
        if miles:
            ax_pace.plot(miles, paces, 'o-', color=color, label=label,
                         linewidth=1.2, markersize=4)

        # Average VO2% vs cumulative distance
        miles_v = [r['cumulative_miles'] for r in res if r['avg_vo2_pct'] > 0]
        vo2s    = [r['avg_vo2_pct']      for r in res if r['avg_vo2_pct'] > 0]
        if miles_v:
            ax_vo2.plot(miles_v, vo2s, 'o-', color=color, label=label,
                        linewidth=1.2, markersize=4)

        # Cumulative carbs vs cumulative distance
        cum_carb = 0.0
        cum_carbs_list = []
        for r in res:
            cum_carb += r['section_carb_g']
            cum_carbs_list.append(cum_carb)
        ax_carb.plot([r['cumulative_miles'] for r in res], cum_carbs_list,
                     'o-', color=color, label=label, linewidth=1.2, markersize=4)

    # Cutoff lines on distance-time
    for r in scenario_results['expected']:
        if r['cutoff_h'] is not None:
            ax_dist.axvline(r['cutoff_h'], color='red', linewidth=0.6,
                            linestyle=':', alpha=0.5)

    ax_dist.set_xlabel('Time (h)')
    ax_dist.set_ylabel('Distance (km)')
    ax_dist.set_title('Distance vs Time')
    ax_dist.legend(fontsize=8)
    ax_dist.grid(color='lightgrey', linewidth=0.6)

    ax_pace.set_xlabel('Cumulative Distance (miles)')
    ax_pace.set_ylabel('Pace (min/mile)')
    ax_pace.set_title('Section Pace')
    ax_pace.invert_yaxis()
    ax_pace.legend(fontsize=8)
    ax_pace.grid(color='lightgrey', linewidth=0.6)

    ax_vo2.set_xlabel('Cumulative Distance (miles)')
    ax_vo2.set_ylabel('% VO₂max')
    ax_vo2.set_title('Average Intensity per Section')
    ax_vo2.legend(fontsize=8)
    ax_vo2.grid(color='lightgrey', linewidth=0.6)

    ax_carb.set_xlabel('Cumulative Distance (miles)')
    ax_carb.set_ylabel('Cumulative Carbs (g)')
    ax_carb.set_title('Cumulative Carbohydrate Demand')
    ax_carb.legend(fontsize=8)
    ax_carb.grid(color='lightgrey', linewidth=0.6)

    fig.suptitle(f"Race Plan  ·  Start {start_dt.strftime('%Y-%m-%d %H:%M')}",
                 fontsize=13, fontweight='bold')
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Plot saved: {output_path}")
    plt.show()


# ── Excel output ─────────────────────────────────────────────────────────────

def make_excel(scenario_results: dict, scenario_configs: dict,
               start_dt: datetime.datetime, output_path: str):
    from openpyxl import Workbook
    from openpyxl.styles import (Font, PatternFill, Alignment, Border, Side,
                                 numbers)
    from openpyxl.utils import get_column_letter

    FILL_HEADER  = PatternFill('solid', fgColor='1F497D')
    FILL_CREW    = PatternFill('solid', fgColor='E2EFDA')   # green tint
    FILL_DROPBAG = PatternFill('solid', fgColor='FFF2CC')   # yellow tint
    FILL_H2O     = PatternFill('solid', fgColor='DDEBF7')   # blue tint
    FILL_CUTOFF  = PatternFill('solid', fgColor='FCE4D6')   # orange/red tint
    FONT_HEADER  = Font(name='Arial', bold=True, color='FFFFFF', size=9)
    FONT_BODY    = Font(name='Arial', size=9)
    FONT_WARN    = Font(name='Arial', size=9, color='C00000', bold=True)
    THIN         = Side(border_style='thin', color='BFBFBF')
    BORDER       = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    COLUMNS = [
        ('Aid Station',         28, '@'),
        ('Mile',                 6, '0.0'),
        ('Elapsed',              8, '@'),
        ('Wall Time',            9, '@'),
        ('Cutoff Buf',           9, '@'),
        ('Pace /mi',             8, '@'),
        ('VO₂%',                 6, '0.0'),
        ('Sec Kcal',             8, '#,##0'),
        ('Sec Carbs (g)',        10, '#,##0'),
        ('Carbs/hr (g)',          9, '0.0'),
        ('Crew Carbs (g)',       11, '#,##0'),
        ('Bags (95g)',            8, '0'),
        ('Water (L)',             8, '0.00'),
        ('Sweat L/hr',           9, '0.000'),
        ('Temp °C',              7, '0.0'),
        ('Wet Bulb °C',          9, '0.0'),
        ('Humidity %',           9, '0'),
        ('Cloud %',              7, '0'),
        ('+Gain (m)',             8, '#,##0'),
        ('-Loss (m)',             8, '#,##0'),
        ('Drop Bag',             7, '@'),
        ('Crew',                 5, '@'),
        ('Pacer',                6, '@'),
        ('Aid Type',             8, '@'),
    ]

    wb = Workbook()
    wb.remove(wb.active)

    def write_sheet(ws, results, label, color_hex):
        # Title row
        ws.append([label, f"Start: {start_dt.strftime('%Y-%m-%d %H:%M')}"])
        ws['A1'].font = Font(name='Arial', bold=True, size=11)
        ws.append([])

        # Header row
        ws.append([c[0] for c in COLUMNS])
        for col_i, (_, width, _) in enumerate(COLUMNS, 1):
            cell = ws.cell(row=3, column=col_i)
            cell.font    = FONT_HEADER
            cell.fill    = FILL_HEADER
            cell.alignment = Alignment(horizontal='center', wrap_text=True)
            cell.border  = BORDER
            ws.column_dimensions[get_column_letter(col_i)].width = width
        ws.row_dimensions[3].height = 30

        # Data rows
        for r in results:
            carbs_hr = (r['section_carb_g'] / (r['section_dur_s'] / 3600.0)
                        if r['section_dur_s'] > 0 else 0.0)
            row = [
                r['name'],
                r['cumulative_miles'],
                _fmt_elapsed(r['elapsed_s']),
                r['wall_time'].strftime('%a %H:%M'),
                _fmt_buffer(r['cutoff_buffer_h']),
                _fmt_pace(r['pace_min_mile']),
                r['avg_vo2_pct'],
                r['metabolic_kcal'],
                r['section_carb_g'],
                carbs_hr,
                r['crew_carb_g'] if r['crew_carb_g'] is not None else '',
                r['bags_to_next_crew'] if r['bags_to_next_crew'] is not None else '',
                r['water_l'],
                r['sweat_rate'],
                r['temp_c'],
                r['wet_bulb'],
                r['humidity'],
                r['cloud'],
                r['elev_gain_m'],
                r['elev_loss_m'],
                'Yes' if r['drop_bag'] else 'No',
                'Yes' if r['crew']     else 'No',
                'Yes' if r['pacer']    else 'No',
                r['aid_type'],
            ]
            ws.append(row)
            data_row = ws.max_row

            # Row fill based on station type
            if r['aid_type'] == 'H2O Only':
                fill = FILL_H2O
            elif r['drop_bag']:
                fill = FILL_DROPBAG
            elif r['crew']:
                fill = FILL_CREW
            else:
                fill = None

            # Override: cutoff danger
            over_cutoff = (r['cutoff_buffer_h'] is not None and r['cutoff_buffer_h'] < 0)

            for col_i, (_, _, fmt) in enumerate(COLUMNS, 1):
                cell = ws.cell(row=data_row, column=col_i)
                cell.border = BORDER
                cell.font   = FONT_WARN if over_cutoff else FONT_BODY
                cell.alignment = Alignment(horizontal='center' if col_i > 1 else 'left')
                if fill and not over_cutoff:
                    cell.fill = fill
                elif over_cutoff:
                    cell.fill = FILL_CUTOFF
                if fmt != '@' and isinstance(cell.value, (int, float)):
                    cell.number_format = fmt

        # Totals row
        totals_row = ws.max_row + 1
        total_carb  = sum(r['section_carb_g']  for r in results)
        total_water = sum(r['water_l']          for r in results)
        total_kcal  = sum(r['metabolic_kcal']   for r in results)
        finish_r    = results[-1]
        ws.cell(totals_row, 1, 'TOTAL').font = Font(name='Arial', bold=True, size=9)
        ws.cell(totals_row, 2, finish_r['cumulative_miles']).font = Font(name='Arial', bold=True, size=9)
        ws.cell(totals_row, 3, _fmt_elapsed(finish_r['elapsed_s'])).font = Font(name='Arial', bold=True, size=9)
        ws.cell(totals_row, 8, total_kcal).number_format = '#,##0'
        ws.cell(totals_row, 8).font = Font(name='Arial', bold=True, size=9)
        ws.cell(totals_row, 9, total_carb).number_format  = '#,##0'
        ws.cell(totals_row, 9).font = Font(name='Arial', bold=True, size=9)
        ws.cell(totals_row, 13, total_water).number_format = '0.0'
        ws.cell(totals_row, 13).font = Font(name='Arial', bold=True, size=9)

        # Legend
        leg_row = totals_row + 2
        ws.cell(leg_row,   1, 'Legend:').font = Font(name='Arial', bold=True, size=8)
        ws.cell(leg_row+1, 1, 'Drop bag station').fill = FILL_DROPBAG
        ws.cell(leg_row+1, 1).font = Font(name='Arial', size=8)
        ws.cell(leg_row+2, 1, 'Crew-accessible station').fill = FILL_CREW
        ws.cell(leg_row+2, 1).font = Font(name='Arial', size=8)
        ws.cell(leg_row+3, 1, 'Water-only station').fill = FILL_H2O
        ws.cell(leg_row+3, 1).font = Font(name='Arial', size=8)
        ws.cell(leg_row+4, 1, 'Past cutoff').fill = FILL_CUTOFF
        ws.cell(leg_row+4, 1).font = Font(name='Arial', bold=True, color='C00000', size=8)

        ws.freeze_panes = 'A4'

    # Scenario sheets
    scenario_order = ['best', 'expected', 'worst']
    for key in scenario_order:
        cfg = scenario_configs[key]
        ws  = wb.create_sheet(title=cfg['label'][:31])
        write_sheet(ws, scenario_results[key], cfg['label'], cfg['color'])

    # Summary comparison sheet
    ws_sum = wb.create_sheet(title='Summary', index=0)
    ws_sum.append(['Race Plan Summary', f"Start: {start_dt.strftime('%Y-%m-%d %H:%M')}"])
    ws_sum['A1'].font = Font(name='Arial', bold=True, size=11)
    ws_sum.append([])

    # Header
    sum_cols = ['Aid Station', 'Mile'] + \
               [f"{scenario_configs[k]['label']} ETA" for k in scenario_order] + \
               [f"{scenario_configs[k]['label']} Cutoff Buf" for k in scenario_order] + \
               ['Expected Carbs (g)', 'Expected Water (L)',
                '+Gain (m)', '-Loss (m)', 'Crew/Drop/Pacer']
    ws_sum.append(sum_cols)
    for col_i in range(1, len(sum_cols) + 1):
        cell = ws_sum.cell(row=3, column=col_i)
        cell.font  = FONT_HEADER
        cell.fill  = FILL_HEADER
        cell.alignment = Alignment(horizontal='center', wrap_text=True)
        cell.border = BORDER
    ws_sum.column_dimensions['A'].width = 28
    ws_sum.column_dimensions['B'].width = 6
    for ci in range(3, len(sum_cols) + 1):
        ws_sum.column_dimensions[get_column_letter(ci)].width = 14
    ws_sum.row_dimensions[3].height = 30

    n_stations = len(scenario_results['expected'])
    for si in range(n_stations):
        re = scenario_results['expected'][si]
        row = [re['name'], re['cumulative_miles']] + \
              [scenario_results[k][si]['wall_time'].strftime('%a %H:%M') for k in scenario_order] + \
              [_fmt_buffer(scenario_results[k][si]['cutoff_buffer_h']) for k in scenario_order] + \
              [re['section_carb_g'], re['water_l'],
               re['elev_gain_m'], re['elev_loss_m'],
               ('D' if re['drop_bag'] else '') +
               ('C' if re['crew']     else '') +
               ('P' if re['pacer']    else '')]
        ws_sum.append(row)
        dr = ws_sum.max_row
        if re['aid_type'] == 'H2O Only':
            fill = FILL_H2O
        elif re['drop_bag']:
            fill = FILL_DROPBAG
        elif re['crew']:
            fill = FILL_CREW
        else:
            fill = None
        for ci in range(1, len(sum_cols) + 1):
            cell = ws_sum.cell(dr, ci)
            cell.border = BORDER
            cell.font   = FONT_BODY
            cell.alignment = Alignment(horizontal='center' if ci > 1 else 'left')
            if fill:
                cell.fill = fill
            # Red text for scenarios past cutoff
            for ki, key in enumerate(scenario_order):
                col_buf = 2 + len(scenario_order) + ki + 1
                if ci == col_buf:
                    buf = scenario_results[key][si]['cutoff_buffer_h']
                    if buf is not None and buf < 0:
                        cell.font = Font(name='Arial', size=9, color='C00000', bold=True)

    ws_sum.freeze_panes = 'A4'

    wb.save(output_path)
    print(f"Excel saved: {output_path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Ultra race day planner using the bonk physics model.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('gpx',           help='GPX course file')
    parser.add_argument('aid_stations',  help='Aid stations JSON')
    parser.add_argument('athlete',       help='Athlete JSON (from calibrate.py)')
    parser.add_argument('--mass',        type=float, default=None)
    parser.add_argument('--glucose',     type=float, default=60.0,
                        help='External carb intake g/hr (default 60)')
    parser.add_argument('--bag-size',    type=float, default=None,
                        help='Grams per nutrition bag (default 95)')
    parser.add_argument('--output',      default=None,
                        help='Base path for output files')
    parser.add_argument('--no-excel',    action='store_true')
    parser.add_argument('--no-plot',     action='store_true')
    args = parser.parse_args()

    # ── Load inputs ──
    with open(args.aid_stations) as f:
        race_cfg = json.load(f)
    with open(args.athlete) as f:
        athlete_params = json.load(f)

    stations      = race_cfg['aid_stations']
    scenario_cfgs = race_cfg['scenarios']
    bag_size_g    = args.bag_size or race_cfg.get('bag_size_g', 95)
    mass          = args.mass or athlete_params.get('mass', 65.0)

    race_name  = race_cfg.get('race_name', os.path.splitext(os.path.basename(args.gpx))[0])
    race_date  = race_cfg.get('race_date', '2026-06-06')
    start_time = race_cfg.get('start_time', '09:00:00')
    start_dt   = datetime.datetime.fromisoformat(f"{race_date}T{start_time}")
    lat        = race_cfg.get('start_lat', 42.33)
    lon        = race_cfg.get('start_lon', -84.24)

    out_base   = args.output or os.path.splitext(os.path.basename(args.gpx))[0].replace(' ', '_')
    if args.athlete and args.athlete != 'athlete.json':
        athlete_stem = os.path.splitext(os.path.basename(args.athlete))[0]
        out_base = out_base + '_' + athlete_stem
    cache_path = out_base + '_weather_cache.json'

    log_path = out_base + '_plan.txt'
    tee = _Tee(log_path)

    print(f"\n{'='*70}")
    print(f"  {race_name}")
    print(f"  Start: {start_dt.strftime('%Y-%m-%d %H:%M')}  |  Mass: {mass} kg")
    print(f"{'='*70}")

    # ── Load course ──
    print("\nLoading course…")
    course = bonk.gpx_to_course(args.gpx)
    total_gpx_m = course.segments[-1].x1
    nominal_m   = race_cfg.get('total_nominal_miles', 100.0) * 1609.34
    scale       = total_gpx_m / nominal_m
    print(f"  Course: {total_gpx_m/1000:.1f} km  "
          f"({total_gpx_m/1609.34:.1f} mi)  "
          f"scale={scale:.4f}")

    # GPX cumulative distances for station matching
    _, gpx_cum_m = gpx_cumulative_distances(args.gpx)

    # ── Weather ──
    print("\nWeather…")
    max_k   = max(float(v['k']) for v in scenario_cfgs.values())
    # Estimate worst-case duration for weather window
    est_dur_h = 40.0
    weather   = load_weather(lat, lon, start_dt, est_dur_h, cache_path)

    # Average temperature over estimated race window for athlete model
    est_end_dt = start_dt + datetime.timedelta(hours=est_dur_h)
    avg_w      = average_weather(weather, start_dt, est_end_dt)
    avg_temp_c = avg_w['temperature_2m']
    print(f"  Average race temperature: {avg_temp_c:.1f}°C")

    # ── Build athlete & environment ──
    def make_athlete(temp_c):
        return bonk.Athlete(
            mass              = mass,
            Ecor              = athlete_params.get('Ecor', 0.98),
            Cd                = athlete_params.get('Cd', 0.5),
            frontalArea       = athlete_params.get('frontalArea', 0.5),
            vo2maxPower       = athlete_params.get('vo2maxPower', 347),
            glucoseConsumption= args.glucose,
            startingGlycogen  = 1500,
            temp              = temp_c,
            altitude          = 0,
        )

    def make_env(temp_c):
        return bonk.Environment(temperature=temp_c, wind=0, altitude=0)

    # ── Athlete assumptions & equivalent flat reference times ──
    ref_athlete_cold = make_athlete(5.0)   # bonk uses 5°C as reference for vo2maxPower
    ref_athlete_race = make_athlete(avg_temp_c)
    # powerDuration.vo2maxPower is altitude-corrected but not temperature-adjusted.
    # Temperature correction = 1/(1 + tempFrac) is applied inside getPower().
    vo2max_power_base = ref_athlete_cold.powerDuration.vo2maxPower   # @ 5°C sea level
    pd_race = ref_athlete_race.powerDuration
    vo2max_power_race = pd_race.vo2maxPower / (1.0 + pd_race.tempFrac)  # temp-adjusted

    def _flat_reference_time(dist_m: float, temp_c: float, name: str) -> float:
        """Return predicted finish time (s) on a perfectly flat course of dist_m."""
        n_segs  = max(10, int(dist_m / 1000))
        seg_len = dist_m / n_segs
        flat_segs = [bonk.Segment(i, seg_len, 0.0, 0.0, 0.0) for i in range(n_segs)]
        flat_course = bonk.Course(flat_segs, name=name)
        flat_env     = make_env(temp_c)
        flat_athlete = make_athlete(temp_c)
        flat_perf    = bonk.Performance(flat_env, flat_athlete, flat_course)
        flat_perf.getRaceTime()
        return flat_perf.duration

    flat_100_s   = _flat_reference_time(100.0 * 1609.34, avg_temp_c, 'Flat 100 mi')
    flat_mara_s  = _flat_reference_time(42195.0,          avg_temp_c, 'Flat Marathon')

    def _fmt_hms(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h}:{m:02d}:{s:02d}"

    print(f"\n{'─'*70}")
    print(f"  Athlete assumptions")
    print(f"{'─'*70}")
    print(f"  Mass:           {mass:.1f} kg")
    print(f"  Ecor:           {athlete_params.get('Ecor', 0.98):.3f}  (metabolic cost of running, J/kg/m)")
    print(f"  VO2max power:   {vo2max_power_base:.0f} W  "
          f"(calibrated at 5°C reference, sea level)")
    print(f"  VO2max power:   {vo2max_power_race:.0f} W  "
          f"(temperature-adjusted @ {avg_temp_c:.1f}°C race avg)")
    # Convert mechanical VO2max power → VO2max in mL/kg/min
    # Metabolic power = mechanical / efficiency (0.25)
    # 1 mL O2 ≈ 20.1 J (mixed diet, RQ ~0.85)
    vo2max_ml = (vo2max_power_race / METABOLIC_EFFICIENCY) * 60.0 / (20100.0 * mass) * 1000.0
    print(f"  VO2max equiv:   ~{vo2max_power_race / mass:.1f} W/kg  "
          f"(≈{vo2max_ml:.0f} mL/kg/min VO₂max)")
    print(f"\n  Equivalent flat-course reference times (@ {avg_temp_c:.1f}°C, no fatigue):")
    print(f"    Flat marathon: {_fmt_hms(flat_mara_s)}")
    print(f"    Flat 100 mi:   {_fmt_hms(flat_100_s)}")
    print(f"{'─'*70}")

    # ── Run scenarios ──
    print("\nRunning scenarios…")
    all_perfs    = {}
    all_results  = {}
    vo2max_eff   = make_athlete(avg_temp_c).powerDuration.vo2maxPower

    for key, cfg in scenario_cfgs.items():
        k_val    = float(cfg['k'])
        athlete  = make_athlete(avg_temp_c)
        env      = make_env(avg_temp_c)
        perf     = run_scenario(course, athlete, env, k_val, weather, start_dt)
        p0       = perf.powerGuess
        # Temperature modifiers: range of correction across race
        mods = [_temp_power_factor(
                    weather_at(weather, start_dt + datetime.timedelta(seconds=perf.durations[i]))
                        ['temperature_2m'],
                    avg_temp_c)
                for i in range(0, len(perf.durations), max(1, len(perf.durations)//10))]
        mod_min, mod_max = min(mods), max(mods)
        print(f"  {cfg['label']:<30}  finish {_fmt_elapsed(perf.duration)}  "
              f"P₀={p0:.0f}W  k={k_val:.5f}/km  "
              f"temp corr [{mod_min:.3f}–{mod_max:.3f}]")

        results = build_station_results(
            perf, stations, gpx_cum_m, scale,
            start_dt, weather, vo2max_eff, bag_size_g)

        all_perfs[key]   = perf
        all_results[key] = results

    # ── Console output ──
    for key, cfg in scenario_cfgs.items():
        print_scenario_table(cfg['label'], all_results[key])

    # ── Plots ──
    if not args.no_plot:
        plot_path = out_base + '_plan.png'
        make_plots(all_results, scenario_cfgs, all_perfs, start_dt,
                   gpx_cum_m, plot_path)

    # ── Excel ──
    if not args.no_excel:
        excel_path = out_base + '_plan.xlsx'
        make_excel(all_results, scenario_cfgs, start_dt, excel_path)

    # ── Close log ──
    tee.close()
    print(f"Log saved: {log_path}")


if __name__ == '__main__':
    main()
