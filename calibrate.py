#!/usr/bin/env python3
"""
Fit athlete parameters to actual race results from GPX files.

Finds the values of Ecor and vo2maxPower (and optionally Cd, frontalArea) that
minimise the total relative error across all supplied races. Mass and environmental
conditions are provided per-race; the fitted parameters are the same for all races.

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


def objective(x, param_names, fixed_params, race_configs, courses, actual_times):
    """Sum of squared relative time errors across all races."""
    params = {**fixed_params, **dict(zip(param_names, x))}
    total = 0.0
    for config, course, actual in zip(race_configs, courses, actual_times):
        try:
            athlete = bonk.Athlete(
                mass=config['mass'],
                Ecor=params['Ecor'],
                Cd=params['Cd'],
                frontalArea=params['frontalArea'],
                vo2maxPower=params['vo2maxPower'],
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
            predicted, _ = perf.getRaceTime()
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
    x0 = np.array([PARAM_DEFAULTS[p] for p in param_names])
    bounds = [PARAM_BOUNDS[p] for p in param_names]

    print(f'\nFitting: {param_names}')
    result = minimize(
        objective,
        x0,
        args=(param_names, fixed_params, races, courses, actual_times),
        method='L-BFGS-B',
        bounds=bounds,
        options={'ftol': 1e-12, 'gtol': 1e-8, 'maxiter': 500},
    )

    if not result.success:
        print(f'Warning: optimizer did not fully converge ({result.message})')

    fitted = {**fixed_params, **dict(zip(param_names, result.x))}

    print('\nFitted parameters:')
    for k in ['Ecor', 'vo2maxPower', 'Cd', 'frontalArea']:
        marker = ' *' if k in param_names else ''
        print(f'  {k:<16s} {fitted[k]:.4f}{marker}')

    # Final predictions with fitted params
    print('\nPredicted vs actual:')
    for race, course, actual in zip(races, courses, actual_times):
        athlete = bonk.Athlete(
            mass=race['mass'],
            Ecor=fitted['Ecor'],
            Cd=fitted['Cd'],
            frontalArea=fitted['frontalArea'],
            vo2maxPower=fitted['vo2maxPower'],
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
        predicted, _ = perf.getRaceTime()
        h_a, m_a, s_a = bonk.getTime(actual)
        h_p, m_p, s_p = bonk.getTime(predicted)
        err = (predicted - actual) / actual * 100
        print(f'  {os.path.basename(race["gpx"]):<30s}  '
              f'actual {int(h_a):02d}:{int(m_a):02d}:{int(s_a):02d}  '
              f'predicted {int(h_p):02d}:{int(m_p):02d}:{int(s_p):02d}  '
              f'({err:+.1f}%)')

    bonk.save_athlete(fitted, args.output)
    print(f'\nSaved to {args.output}')


if __name__ == '__main__':
    main()
