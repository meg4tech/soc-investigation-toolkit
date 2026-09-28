"""Detection configuration.

Precedence (highest first): command-line override, JSON config file,
built-in default. The source of the active threshold is recorded so the
report can state exactly which threshold produced its findings.
"""

import json
import math
from dataclasses import dataclass
from pathlib import Path

# Roughly the cruising speed of a commercial airliner. Logins that would
# require travelling faster than this are hard to explain by real travel.
DEFAULT_MAX_SPEED_KMH = 900.0

ALLOWED_CONFIG_KEYS = {"max_speed_kmh"}


class ConfigError(ValueError):
    """Raised when configuration is missing, malformed or out of range."""


@dataclass(frozen=True)
class DetectionConfig:
    max_speed_kmh: float
    source: str


def validate_max_speed(value: object, source: str) -> float:
    """Return `value` as a float if it is a usable speed threshold."""
    # bool is a subclass of int in Python, so reject it explicitly:
    # `true` in a JSON file must not silently become a threshold of 1 km/h.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{source}: max_speed_kmh must be a number, got {value!r}")
    speed = float(value)
    # NaN or infinity would make every comparison false, silently disabling
    # the detection, so they are rejected rather than accepted.
    if not math.isfinite(speed) or speed <= 0:
        raise ConfigError(
            f"{source}: max_speed_kmh must be a positive finite number, got {value!r}"
        )
    return speed


def load_config(
    config_path: str | Path | None = None,
    max_speed_override: float | None = None,
) -> DetectionConfig:
    """Build the active detection configuration."""
    config = DetectionConfig(DEFAULT_MAX_SPEED_KMH, "built-in default")

    if config_path is not None:
        config = _load_config_file(Path(config_path))

    if max_speed_override is not None:
        source = "command line (--max-speed-kmh)"
        config = DetectionConfig(validate_max_speed(max_speed_override, source), source)

    return config


def _load_config_file(path: Path) -> DetectionConfig:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as exc:
        raise ConfigError(f"Cannot read config file {path}: {exc.strerror}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ConfigError(f"Config file {path} is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"Config file {path} must contain a JSON object")

    # Reject unknown keys so a typo (e.g. "max_speed_kph") fails loudly
    # instead of the analyst unknowingly running with a different threshold.
    unknown = set(data) - ALLOWED_CONFIG_KEYS
    if unknown:
        raise ConfigError(f"Config file {path} has unknown keys: {sorted(unknown)}")
    if "max_speed_kmh" not in data:
        raise ConfigError(f"Config file {path} is missing 'max_speed_kmh'")

    source = f"config file {path}"
    return DetectionConfig(validate_max_speed(data["max_speed_kmh"], source), source)
