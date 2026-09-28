# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

SOC Investigation Toolkit is a defensive cybersecurity project: a modular toolkit to help SOC analysts investigate security alerts. The long-term scope includes Python, Microsoft Sentinel/KQL, PowerShell and security enrichment APIs.

The author is a cybersecurity and digital forensics student. Code must be production-minded **and** easy to understand and explain component by component. Favor clarity over cleverness.

## Current scope: Version 0.1 — Impossible Travel detection only

v0.1 (implemented):
- Read synthetic login events (user, timestamp, IP address, latitude, longitude, location).
- Correlate consecutive logins for the same user.
- Calculate geographic distance, elapsed time, and the travel speed required between them.
- Flag pairs where required speed exceeds a configurable threshold.
- Produce a clear SOC-style investigation result.
- Include tests.

Explicitly **out of scope** for v0.1: Azure, Microsoft Sentinel, KQL, PowerShell, external/enrichment APIs, IP geolocation lookups, network access of any kind. Do not add functionality beyond v0.1 (extra detections, severity scoring, enrichment, dashboards, new data sources, etc.) without discussing it with the user first.

## Architecture (v0.1)

Update this section when the layout changes.

```
soc_toolkit/
  models.py            # Frozen dataclasses: LoginEvent, TravelAssessment
  loader.py            # Read CSV, validate every field, return LoginEvents (UTC)
  geo.py               # Haversine great-circle distance (km)
  impossible_travel.py # Group by user, sort by time, pair consecutive logins,
                       # compute distance/elapsed/speed, compare to threshold
  config.py            # DEFAULT_MAX_SPEED_KMH (900), JSON config file, CLI override
  report.py            # Render SOC-style investigation output
  cli.py               # argparse, wires the stages together, sets exit code
  __main__.py          # `python -m soc_toolkit` entry point -> cli.main()
config/impossible_travel.json   # Example config, used only when passed via --config
data/sample/                    # Synthetic data only; files must be named "synthetic_*"
tests/                          # unittest; one test module per package module
```

Data flow: `cli` → `config` + `loader` → `impossible_travel` (uses `geo`) → `report`. `impossible_travel`, `geo` and `report` are pure (no file I/O, no printing) so they can be unit-tested with in-memory events. Only `cli` prints.

Key detection rules:
- Timestamps must be ISO 8601 **with timezone offset** (`Z` accepted); naive timestamps are rejected rather than guessed. Everything is normalized to UTC before computing elapsed time.
- Users are compared case-insensitively (lowercased on load).
- Pairing is strictly *consecutive* logins per user after sorting by (timestamp, source_row).
- Flag when speed is **strictly greater** than the threshold.
- Same timestamp + different location → `InvalidTravelPairError`; the run stops. Same timestamp + same location (duplicate) → 0 km/h, not flagged.
- Any invalid row or pair stops the whole run with exit code 1 and **no partial report**, since a partial report could look complete while missing a detection.
- Text fields containing control or format characters (Unicode Cc/Cf, e.g. ANSI escapes or bidi overrides) are rejected, so log content cannot manipulate the analyst's terminal output.
- Threshold precedence: `--max-speed-kmh` > `--config` file > built-in default. The report prints the active threshold and its source. Config files with unknown keys, and non-positive or non-finite thresholds, are rejected.
- Every `LoginEvent` carries `source_row` so findings can be traced back to the input line.

Exit codes: 0 completed (with or without findings), 1 invalid input/config, 2 argparse usage error.

## Commands

Python 3.10+, standard library only (no runtime dependencies; tests use `unittest`).

```
python -m soc_toolkit data/sample/synthetic_logins.csv                      # run detection
python -m soc_toolkit data/sample/synthetic_logins.csv --config config/impossible_travel.json
python -m soc_toolkit data/sample/synthetic_logins.csv --max-speed-kmh 500  # override threshold
python -m unittest discover -s tests -v                                     # all tests
python -m unittest tests.test_geo                                           # one module
python -m unittest tests.test_geo.TestHaversine.test_known_distance         # one test
```

Keep this section accurate if module names or CLI flags change.

## Development principles

- Readable, maintainable Python; type hints and dataclasses; small functions with one responsibility.
- Comment the *security reasoning* (why a check exists, what an attacker or bad data could do), not what the syntax does.
- Avoid external dependencies. Adding any dependency requires discussion with the user first.
- Tests cover: haversine against known distances, speed calculation, threshold boundary (just below / equal / just above), zero-elapsed case, multiple users interleaved, unsorted input, and each input-validation failure.
- Error handling fails safely: bad input produces a clear error, never a silent skip that could hide a detection or a fabricated value.

## Security requirements

- Never hard-code credentials, API keys, secrets or tokens. Future integrations must read them from environment variables or a secret store, never from committed files.
- Never fabricate investigation evidence. Output only values derived from the input data; if a value is missing or cannot be computed, say so explicitly.
- Detection thresholds are configurable, never hard-coded.
- Validate all input data and handle errors safely.
- Sample data is synthetic only and must be clearly labeled as such (filename prefix and a note in the file/README). Never commit real user, IP or authentication data.
- Automated output is **investigation support, not a final determination of compromise.** Every report must state this and note limitations (e.g. IP geolocation inaccuracy, VPN/proxy use, shared or mobile IPs) that an analyst must verify.
