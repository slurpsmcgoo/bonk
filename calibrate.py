#!/usr/bin/env python3
"""
Fit athlete parameters to actual race results from GPX files.

Finds the values of Ecor and vo2maxPower (and optionally Cd, frontalArea) that
minimise the total relative error across all supplied races. Each race also gets its
own ecor_mod (surface difficulty factor) so that trail and road races can be compared
against each other without biasing the shared athlete parameters.

Usage:
    python calibrate.py races.json
    python calibrate.py races.json --output jack.json
    python calibrate.py races.json --fit-params Ecor vo2maxPower Cd frontalArea

Config JSON format:
    {
      "races": [
        {
          "gpx":               "path/to/race.gpx",   <- required
          "mass":              65,                    <- required (kg)
          "actual_time":       "2:49:53",             <- optional if GPX has timestamps
          "temperature":       15,                    <- optional (°C,  default 5)
          "wind":              0,                     <- optional (m/s, default 0)
          "altitude":          0,                     <- optional (m,   default 0)
          "glucoseConsumption": 60,                   <- optional (g/h, default 60)
          "startingGlycogen":  1500                   <- optional (kcal,default 1500)
        }
      ],
      "fit_params": ["Ecor", "vo2maxPower"]           <- optional
    }
"""

import argparse
import json
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'source'))
import bonk


PARAM_BOUNDS = {
    'Ecor':        (0.5,  2.0),
    'vo2maxPower': (100,  800),
    'Cd':          (0.1,  1.5),
    'frontalArea': (0.1,  1.5),
}

PARAM_DEFAULTS = {
    'Ecor':        0.98,
    'vo2maxPower': 347,
    'Cd':          0.5,
    'frontalArea': 0.5,
}

ECOR_MOD_BOUNDS = (0.0, 1.0)
K_BOUNDS = (0.0, 0.05)   # fatigue decay per km; 0.02 → ~85% capacity at marathon, ~33% at 100mi


def gpx_actual_splits(gpx_path):
    """Extract cumulative distance (km) and elapsed time (hours) from GPX timestamps.

    Returns (times_h, distances_km) as numpy arrays, or (None, None) if no timestamps.
    """
    import gpxpy
    with open(gpx_path) as f:
        gpx = gpxpy.parse(f)
    points = [p for t in gpx.tracks for s in t.segments for p in s.points]
    times = [p.time for p in points]
    if any(t is None for t in times):
        return None, None
    t0 = min(times)
    elapsed = np.array([(t - t0).total_seconds() for t in times]) / 3600.0
    lats = np.array([p.latitude for p in points])
    lons = np.array([p.longitude for p in points])
    dists = np.zeros(len(points))
    for i in range(1, len(points)):
        dists[i] = dists[i - 1] + bonk.haversine(lats[i-1], lons[i-1], lats[i], lons[i]) / 1000.0
    return elapsed, dists


def parse_time(s):
    """Parse 'H:MM:SS' or 'HH:MM:SS' string to total seconds."""
    parts = s.strip().split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    raise ValueError(f"Cannot parse time '{s}' — expected H:MM:SS or MM:SS")


def gpx_duration(gpx_path):
    """Return elapsed time in seconds from GPX timestamps, or None if unavailable."""
    import gpxpy
    with open(gpx_path) as f:
        gpx = gpxpy.parse(f)
    points = [p for t in gpx.tracks for s in t.segments for p in s.points]
    times = [p.time for p in points if p.time is not None]
    if len(times) < 2:
        return None
    return (max(times) - min(times)).total_seconds()


def objective(x, param_names, fixed_params, race_configs, courses, actual_times, n_races):
    """Sum of squared relative time errors across all races.

    Parameter vector x = [athlete_params..., ecor_mod_0, ..., k_0, ...]
    Athlete params are shared across races. Each race gets its own ecor_mod (surface
    difficulty) and k (fatigue decay constant per km; k=0 → constant-power model).
    """
    n_ap = len(param_names)
    athlete_params = {**fixed_params, **dict(zip(param_names, x[:n_ap]))}
    ecor_mods = x[n_ap:n_ap + n_races]
    ks = x[n_ap + n_races:]

    total = 0.0
    for i, (config, course, actual) in enumerate(zip(race_configs, courses, actual_times)):
        try:
            athlete = bonk.Athlete(
                mass=config['mass'],
                Ecor=athlete_params['Ecor'],
                Cd=athlete_params['Cd'],
                frontalArea=athlete_params['frontalArea'],
                vo2maxPower=athlete_params['vo2maxPower'],
                glucoseConsumption=config.get('glucoseConsumption', 60),
                startingGlycogen=config.get('startingGlycogen', 1500),
                temp=config.get('temperature', 5),
                altitude=config.get('altitude', 0),
            )
            env = bonk.Environment(
                temperature=config.get('temperature', 5),
                wind=config.get('wind', 0),
                altitude=config.get('altitude', 0),
            )
            perf = bonk.Performance(env, athlete, course)
            k = float(ks[i])
            em = float(ecor_mods[i])
            if k == 0.0:
                predicted, _ = perf.getRaceTime(ecor_mod=em)
            else:
                predicted, _ = perf.getUltraRaceTime(k=k, ecor_mod=em)
            total += ((predicted - actual) / actual) ** 2
        except Exception:
            return 1e10
    return total


def main():
    parser = argparse.ArgumentParser(
        description='Fit athlete parameters to race GPX files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('config', help='JSON config file listing races and conditions')
    parser.add_argument('-o', '--output', default='athlete.json',
                        help='Output JSON file for fitted parameters (default: athlete.json)')
    parser.add_argument('--fit-params', nargs='+', metavar='PARAM',
                        choices=list(PARAM_BOUNDS),
                        help='Parameters to fit (overrides config fit_params). '
                             f'Choices: {list(PARAM_BOUNDS)}')
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    races = config['races']
    n_races = len(races)
    param_names = args.fit_params or config.get('fit_params', ['Ecor', 'vo2maxPower'])

    # Resolve actual times — prefer explicit actual_time, fall back to GPX timestamps
    actual_times = []
    for race in races:
        if 'actual_time' in race:
            actual_times.append(parse_time(race['actual_time']))
        else:
            t = gpx_duration(race['gpx'])
            if t is None:
                sys.exit(f"Error: no timestamps in {race['gpx']} and no actual_time provided.")
            actual_times.append(t)

    # Build Course objects once — reused across all optimizer iterations
    print('Loading courses...')
    courses = []
    for race, actual in zip(races, actual_times):
        course = bonk.gpx_to_course(race['gpx'])
        courses.append(course)
        h, m, s = bonk.getTime(actual)
        total_km = course.segments[-1].x1 / 1000
        print(f'  {os.path.basename(race["gpx"]):<30s}  '
              f'actual {int(h):02d}:{int(m):02d}:{int(s):02d}  '
              f'{total_km:.1f} km')

    fixed_params = {k: v for k, v in PARAM_DEFAULTS.items() if k not in param_names}

    # Parameter vector: [athlete_params..., ecor_mod_0, ..., k_0, ...]
    x0 = np.array([PARAM_DEFAULTS[p] for p in param_names] + [0.0] * n_races + [0.0] * n_races)
    bounds = [PARAM_BOUNDS[p] for p in param_names] + [ECOR_MOD_BOUNDS] * n_races + [K_BOUNDS] * n_races

    print(f'\nFitting: {param_names} + ecor_mod + k (fatigue decay) per race ({n_races} races)')
    result = minimize(
        objective,
        x0,
        args=(param_names, fixed_params, races, courses, actual_times, n_races),
        method='L-BFGS-B',
        bounds=bounds,
        options={'ftol': 1e-12, 'gtol': 1e-8, 'maxiter': 500},
    )

    if not result.success:
        print(f'Warning: optimizer did not fully converge ({result.message})')

    n_ap = len(param_names)
    fitted_athlete = {**fixed_params, **dict(zip(param_names, result.x[:n_ap]))}
    fitted_ecor_mods = result.x[n_ap:n_ap + n_races]
    fitted_ks = result.x[n_ap + n_races:]

    print('\nFitted athlete parameters:')
    for key in ['Ecor', 'vo2maxPower', 'Cd', 'frontalArea']:
        marker = ' *' if key in param_names else ''
        print(f'  {key:<16s} {fitted_athlete[key]:.4f}{marker}')

    print('\nFitted per-race parameters:')
    for race, em, k_val in zip(races, fitted_ecor_mods, fitted_ks):
        print(f'  {os.path.basename(race["gpx"]):<30s}  ecor_mod={em:.4f}  k={k_val:.5f}/km')

    # Final predictions with fitted params
    print('\nPredicted vs actual:')
    for i, (race, course, actual) in enumerate(zip(races, courses, actual_times)):
        athlete = bonk.Athlete(
            mass=race['mass'],
            Ecor=fitted_athlete['Ecor'],
            Cd=fitted_athlete['Cd'],
            frontalArea=fitted_athlete['frontalArea'],
            vo2maxPower=fitted_athlete['vo2maxPower'],
            glucoseConsumption=race.get('glucoseConsumption', 60),
            startingGlycogen=race.get('startingGlycogen', 1500),
            temp=race.get('temperature', 5),
            altitude=race.get('altitude', 0),
        )
        env = bonk.Environment(
            temperature=race.get('temperature', 5),
            wind=race.get('wind', 0),
            altitude=race.get('altitude', 0),
        )
        perf = bonk.Performance(env, athlete, course)
        em = float(fitted_ecor_mods[i])
        k_val = float(fitted_ks[i])
        if k_val == 0.0:
            predicted, _ = perf.getRaceTime(ecor_mod=em)
        else:
            predicted, _ = perf.getUltraRaceTime(k=k_val, ecor_mod=em)
        h_a, m_a, s_a = bonk.getTime(actual)
        h_p, m_p, s_p = bonk.getTime(predicted)
        err = (predicted - actual) / actual * 100
        print(f'  {os.path.basename(race["gpx"]):<30s}  '
              f'actual {int(h_a):02d}:{int(m_a):02d}:{int(s_a):02d}  '
              f'predicted {int(h_p):02d}:{int(m_p):02d}:{int(s_p):02d}  '
              f'({err:+.1f}%)')

    bonk.save_athlete(fitted_athlete, args.output)
    print(f'\nSaved athlete parameters to {args.output}')

    # Plot predicted vs actual distance-time and their difference for each race
    n_cols = min(n_races, 2)
    n_race_rows = (n_races + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_race_rows * 2, n_cols,
                             figsize=(7 * n_cols, 8 * n_race_rows), squeeze=False)

    for i, (race, course, actual) in enumerate(zip(races, courses, actual_times)):
        col = i % n_cols
        row = (i // n_cols) * 2
        ax_dist = axes[row][col]
        ax_diff = axes[row + 1][col]

        # Rebuild performance at fitted params to get predicted splits
        athlete = bonk.Athlete(
            mass=race['mass'],
            Ecor=fitted_athlete['Ecor'],
            Cd=fitted_athlete['Cd'],
            frontalArea=fitted_athlete['frontalArea'],
            vo2maxPower=fitted_athlete['vo2maxPower'],
            glucoseConsumption=race.get('glucoseConsumption', 60),
            startingGlycogen=race.get('startingGlycogen', 1500),
            temp=race.get('temperature', 5),
            altitude=race.get('altitude', 0),
        )
        env = bonk.Environment(
            temperature=race.get('temperature', 5),
            wind=race.get('wind', 0),
            altitude=race.get('altitude', 0),
        )
        perf = bonk.Performance(env, athlete, course)
        em = float(fitted_ecor_mods[i])
        k_val = float(fitted_ks[i])
        if k_val == 0.0:
            perf.getRaceTime(ecor_mod=em)
        else:
            perf.getUltraRaceTime(k=k_val, ecor_mod=em)

        pred_times_h = np.array(perf.durations) / 3600.0
        pred_dists_km = np.array(perf.distances) / 1000.0

        name = os.path.basename(race['gpx'])
        k_str = f'  k={k_val:.5f}/km' if k_val > 0 else ''
        title = f'{name}\necor_mod={em:.3f}{k_str}'

        # Top: distance vs time
        ax_dist.plot(pred_times_h, pred_dists_km, label='predicted', color='steelblue', linewidth=1.5)
        act_times_h, act_dists_km = gpx_actual_splits(race['gpx'])
        if act_times_h is not None:
            ax_dist.plot(act_times_h, act_dists_km, label='actual', color='coral',
                         linewidth=1.5, alpha=0.8)
        ax_dist.set_title(title)
        ax_dist.set_xlabel('Time (h)')
        ax_dist.set_ylabel('Distance (km)')
        ax_dist.legend()
        ax_dist.grid(color='lightgrey', linestyle='-', linewidth=0.8)

        # Bottom: predicted - actual distance vs time (interpolate predicted onto actual time grid)
        if act_times_h is not None:
            pred_at_act_times = np.interp(act_times_h, pred_times_h, pred_dists_km)
            diff_km = pred_at_act_times - act_dists_km
            ax_diff.plot(act_times_h, diff_km, color='steelblue', linewidth=1.2)
            ax_diff.axhline(0, color='black', linewidth=0.8, linestyle='--')
            ax_diff.fill_between(act_times_h, diff_km, 0,
                                 where=(diff_km >= 0), alpha=0.2, color='steelblue',
                                 label='model ahead')
            ax_diff.fill_between(act_times_h, diff_km, 0,
                                 where=(diff_km < 0), alpha=0.2, color='coral',
                                 label='model behind')
            ax_diff.set_xlabel('Time (h)')
            ax_diff.set_ylabel('Predicted − actual (km)')
            ax_diff.legend(fontsize=8)
            ax_diff.grid(color='lightgrey', linestyle='-', linewidth=0.8)
        else:
            ax_diff.set_visible(False)

    # Hide any unused subplot pairs
    for j in range(n_races, n_race_rows * n_cols):
        col = j % n_cols
        row = (j // n_cols) * 2
        axes[row][col].set_visible(False)
        axes[row + 1][col].set_visible(False)

    fig.tight_layout()
    plot_path = os.path.splitext(args.config)[0] + '_splits.png'
    fig.savefig(plot_path, dpi=150)
    print(f'Splits plot saved to {plot_path}')
    plt.show()


if __name__ == '__main__':
    main()
