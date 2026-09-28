"""Command-line interface.

Exit codes:
    0  analysis completed (whether or not anything was flagged)
    1  invalid input data or configuration; no report produced
    2  invalid command-line usage (raised by argparse)
"""

import argparse
import sys

from . import __version__
from .config import ConfigError, load_config
from .impossible_travel import InvalidTravelPairError, detect_impossible_travel
from .loader import InputValidationError, load_login_events
from .report import format_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="soc_toolkit",
        description="Impossible Travel detection over login events (investigation support only).",
    )
    parser.add_argument("input", help="CSV file of login events")
    parser.add_argument("--config", help="JSON config file (e.g. config/impossible_travel.json)")
    parser.add_argument(
        "--max-speed-kmh",
        type=float,
        help="override the speed threshold in km/h (takes precedence over --config)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        config = load_config(args.config, args.max_speed_kmh)
        events = load_login_events(args.input)
        assessments = detect_impossible_travel(events, config.max_speed_kmh)
    except (ConfigError, InputValidationError, InvalidTravelPairError) as exc:
        # Stop without a partial report: a report built on part of the data
        # could look complete while missing the pair that mattered.
        print(f"ERROR: {exc}", file=sys.stderr)
        print("No report was produced. Correct the input and run again.", file=sys.stderr)
        return 1

    print(format_report(events, assessments, config, args.input))
    return 0
