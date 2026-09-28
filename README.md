# SOC Investigation Toolkit

A defensive, modular toolkit to support SOC analysts investigating security alerts.

**Version 0.1** provides one capability: **Impossible Travel detection** over login data. It runs locally, uses only the Python standard library, and makes no network connections.

> **Investigation support only.** The toolkit highlights activity that needs a closer look. It does not determine whether an account is compromised; an analyst must verify every finding against the original log sources.

## What is Impossible Travel?

If an account signs in from London and then from Sydney two hours later, the user would have to travel at about 8,500 km/h, which is far faster than any commercial flight. That usually means that someone other than the user is signing in (for example with stolen credentials or a session token), or that something such as a VPN is distorting the location. Either way, it deserves investigation.

## How the detection works

1. **Load and validate.** Each CSV row is checked:
   - required fields are present
   - the IP address is valid
   - latitude and longitude are in range
   - the timestamp is ISO 8601 with a timezone offset
   - no control characters appear
   
   Timestamps are converted to UTC. Any invalid row stops the run with an error naming the row, so a report is never produced from partially valid data.
2. **Correlate.** Logins are grouped by user (case-insensitively), sorted by time, and each login is paired with that user's next login.
3. **Measure.** For each pair the tool calculates:
   - **distance**, using the haversine great-circle formula
   - **elapsed time** between the two logins
   - **required speed** = distance ÷ elapsed time
4. **Flag.** A pair is flagged when the required speed is **strictly greater** than the threshold (900 km/h by default, roughly airliner cruising speed).
5. **Report.** Flagged pairs are printed as SOC-style findings with the evidence (and its source row numbers), suggested analyst checks, and known limitations.

Two edge cases are handled explicitly:

| Case | Behaviour |
|---|---|
| Same timestamp, **different** location | Rejected as invalid data (the run stops). One account cannot be in two places at the same instant, so this points to a data problem that an analyst must resolve first. |
| Same timestamp, **same** location (duplicate) | Accepted. The speed is 0 km/h and the pair is not flagged. |

## Requirements

Python 3.10 or later. There are no third-party dependencies.

## Usage

Run from the project root:

```
python -m soc_toolkit data/sample/synthetic_logins.csv
python -m soc_toolkit data/sample/synthetic_logins.csv --config config/impossible_travel.json
python -m soc_toolkit data/sample/synthetic_logins.csv --max-speed-kmh 500
python -m soc_toolkit --help
```

### Threshold configuration

The speed threshold is set from these sources, highest precedence first:

1. `--max-speed-kmh` on the command line
2. The `--config` JSON file, for example `config/impossible_travel.json`:
   ```json
   { "max_speed_kmh": 900 }
   ```
3. The built-in default of 900 km/h

The report always states which threshold was used and where it came from. Unknown keys in the config file, and non-positive or non-numeric values, are rejected.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Analysis completed (with or without findings) |
| 1 | Invalid input data or configuration; no report produced |
| 2 | Invalid command-line usage |

## Input format

The input is a UTF-8 CSV file with a header row and these columns (extra columns are ignored):

| Column | Example | Rules |
|---|---|---|
| `user` | `alice@example.com` | Required. Compared case-insensitively. |
| `timestamp` | `2026-03-02T09:00:00+00:00` | ISO 8601 **with** a timezone offset (`Z` is accepted). |
| `ip_address` | `192.0.2.10` | Valid IPv4 or IPv6 address. |
| `latitude` | `51.5074` | -90 to 90 |
| `longitude` | `-0.1278` | -180 to 180 |
| `location` | `London, GB` | Required, free text |

## Sample data

`data/sample/synthetic_logins.csv` is **synthetic**. It uses reserved documentation domains and IP ranges, and it covers normal travel, one impossible-travel case, a realistic long-haul flight, a single-login user and a duplicate event. See [data/sample/README.md](data/sample/README.md). Do not commit real authentication data to this repository.

## Running the tests

```
python -m unittest discover -s tests -v                                  # all tests
python -m unittest tests.test_impossible_travel                          # one module
python -m unittest tests.test_geo.TestHaversine.test_known_distance      # one test
```

## Project structure

```
soc_toolkit/
  cli.py                 Command-line interface and exit codes
  loader.py              CSV reading and input validation
  models.py              LoginEvent and TravelAssessment records
  geo.py                 Haversine distance
  config.py              Threshold defaults, config file and override
  impossible_travel.py   Correlation, speed calculation and flagging
  report.py              SOC-style text report
config/                  Example detection configuration
data/sample/             Synthetic sample data only
tests/                   unittest suite (one module per package module)
```

## Limitations

- IP geolocation can be inaccurate, especially for mobile and ISP-assigned addresses.
- VPNs, proxies and cloud services can place a legitimate user far from their real location, which causes false positives.
- Only consecutive logins present in the input file are compared.
- Distances are great-circle estimates, so the required speeds are minimums.
- Input values are trusted as provided. The toolkit does not look up or verify IP locations.

## Scope

Version 0.1 deliberately excludes Azure, Microsoft Sentinel/KQL, PowerShell, external or enrichment APIs, databases, and web or AI features. These are planned for later versions.
