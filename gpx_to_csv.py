import argparse
from source.bonk import gpx_to_course_csv

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Convert a GPX file into a course CSV for bonk.')
    parser.add_argument('gpx_file', help='Path to the input GPX file')
    parser.add_argument('--ecormod', type=float, default=0.0,
                        help='Default EcorMod value for all generated segments')
    parser.add_argument('--surfacetechmod', type=float, default=0.0,
                        help='Default surfaceTechMod value for all generated segments')
    parser.add_argument('-o', '--output', default=None,
                        help='Optional output CSV file path')

    args = parser.parse_args()
    gpx_to_course_csv(
        args.gpx_file,
        ecor_mod=args.ecormod,
        surface_tech_mod=args.surfacetechmod,
        output_csv_path=args.output)
