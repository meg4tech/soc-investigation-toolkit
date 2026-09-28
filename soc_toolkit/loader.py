"""Load and validate login events from a CSV file.

Every row is validated before any detection runs. Invalid data stops the
run with an error naming the row: a detection built on silently skipped or
guessed values could miss real activity or report activity that never happened.
"""

import csv
import ipaddress
import math
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from .models import LoginEvent

REQUIRED_COLUMNS = ("user", "timestamp", "ip_address", "latitude", "longitude", "location")


class InputValidationError(ValueError):
    """Raised when input data is missing, malformed or out of range."""


def load_login_events(path: str | Path) -> list[LoginEvent]:
    """Read `path` and return a validated LoginEvent for every row."""
    path = Path(path)
    try:
        # utf-8-sig tolerates the byte-order mark that Excel adds to CSV exports.
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            _check_columns(reader.fieldnames)
            events = [_parse_row(row, reader.line_num) for row in reader]
    except OSError as exc:
        raise InputValidationError(f"Cannot read input file {path}: {exc.strerror}") from exc
    except UnicodeDecodeError as exc:
        raise InputValidationError(f"Input file {path} is not valid UTF-8") from exc
    except csv.Error as exc:
        raise InputValidationError(f"Input file {path} is not valid CSV: {exc}") from exc

    if not events:
        raise InputValidationError(f"Input file {path} contains no login events")
    return events


def _check_columns(fieldnames: list[str] | None) -> None:
    if not fieldnames:
        raise InputValidationError("Input file is empty or has no header row")
    # A repeated column name makes the file ambiguous: csv.DictReader silently
    # keeps only the last value, so detection could run on a different
    # timestamp, location or user than the analyst sees in the file. Names
    # that differ only in case or surrounding spaces are just as ambiguous.
    normalised = [name.strip().lower() for name in fieldnames]
    duplicates = sorted({name for name in normalised if normalised.count(name) > 1})
    if duplicates:
        raise InputValidationError(f"Input file has duplicate columns: {duplicates}")
    missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing:
        raise InputValidationError(f"Input file is missing required columns: {missing}")


def _parse_row(row: dict, line: int) -> LoginEvent:
    # DictReader stores surplus values under the key None. A row with more
    # values than headers is misaligned, so no field in it can be trusted.
    if None in row:
        raise InputValidationError(f"Row {line}: has more values than the header has columns")

    values = {}
    for column in REQUIRED_COLUMNS:
        value = row.get(column)
        if value is None or not value.strip():
            raise InputValidationError(f"Row {line}: missing value for '{column}'")
        _reject_control_characters(value, column, line)
        values[column] = value.strip()

    return LoginEvent(
        # Account names (e.g. Entra ID UPNs) are case-insensitive. Normalising
        # stops one account being split into two "users", which would hide
        # travel between its logins.
        user=values["user"].lower(),
        timestamp=_parse_timestamp(values["timestamp"], line),
        ip_address=_parse_ip_address(values["ip_address"], line),
        latitude=_parse_coordinate(values["latitude"], "latitude", 90.0, line),
        longitude=_parse_coordinate(values["longitude"], "longitude", 180.0, line),
        location=values["location"],
        source_row=line,
    )


def _reject_control_characters(value: str, column: str, line: int) -> None:
    # Log fields can be attacker-influenced. Control characters (e.g. ANSI
    # terminal escape sequences) and invisible format characters (e.g.
    # right-to-left overrides) could disguise or rewrite what the analyst
    # sees in the report, so they are rejected outright.
    if any(unicodedata.category(char) in ("Cc", "Cf") for char in value):
        raise InputValidationError(
            f"Row {line}: '{column}' contains control or invisible formatting characters"
        )


def _parse_timestamp(value: str, line: int) -> datetime:
    text = value
    # datetime.fromisoformat only accepts the "Z" (UTC) suffix from Python 3.11.
    if text[-1] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise InputValidationError(
            f"Row {line}: timestamp {value!r} is not ISO 8601 "
            "(expected e.g. 2026-03-02T09:00:00+00:00)"
        ) from exc

    # A timestamp without an offset is ambiguous: the same wall-clock time in
    # London and Sydney is ~10 hours apart. Guessing would corrupt the elapsed
    # time and therefore the speed, so the timestamp is rejected instead.
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InputValidationError(
            f"Row {line}: timestamp {value!r} has no timezone offset"
        )
    return parsed.astimezone(timezone.utc)


def _parse_ip_address(value: str, line: int) -> str:
    try:
        # str() gives the canonical form, so equivalent spellings of an
        # IPv6 address are displayed identically in the report.
        return str(ipaddress.ip_address(value))
    except ValueError as exc:
        raise InputValidationError(f"Row {line}: invalid IP address {value!r}") from exc


def _parse_coordinate(value: str, name: str, limit: float, line: int) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise InputValidationError(f"Row {line}: {name} {value!r} is not a number") from exc
    # float() accepts "nan" and "inf", which would poison every distance
    # calculation, so they are rejected along with out-of-range values.
    if not math.isfinite(number) or not -limit <= number <= limit:
        raise InputValidationError(
            f"Row {line}: {name} {value!r} is outside the valid range -{limit:g} to {limit:g}"
        )
    return number
