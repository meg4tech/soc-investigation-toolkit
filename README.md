# SOC Investigation Toolkit

![tests](https://github.com/meg4tech/soc-investigation-toolkit/actions/workflows/tests.yml/badge.svg)

A defensive, modular toolkit to support SOC analysts investigating security alerts.

**Version 0.1** provides one capability: **Impossible Travel detection** over login data. It runs locally, uses only the Python standard library, and makes no network connections.

> **Investigation support only.** The toolkit highlights activity that needs a closer look. It does not determine whether an account is compromised; an analyst must verify every finding against the original log sources.

## What is Impossible Travel?

If an account signs in from London and then from Sydney two hours later, the user would have to travel at about 8,500 km/h, which is far faster than any commercial flight. This can indicate that someone other than the user is signing in (for example with stolen credentials or a stolen session token). In practice, many of these alerts have harmless causes, such as VPNs, mobile networks, or cloud and proxy services that distort the apparent location. Either way, the pair needs investigating before any conclusion is drawn.

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

## Installation

Requires Python 3.10 or later. There are no third-party dependencies, so there is no `pip install` step.

```
git clone https://github.com/meg4tech/soc-investigation-toolkit.git
cd soc-investigation-toolkit
python --version    # must be 3.10 or later
```

Depending on your system, the Python command may be `python3` (macOS and Linux) or `py` (Windows) instead of `python`.

## Usage

Run from the project root:

```
python -m soc_toolkit data/sample/synthetic_logins.csv
python -m soc_toolkit data/sample/synthetic_logins.csv --config config/impossible_travel.json
python -m soc_toolkit data/sample/synthetic_logins.csv --max-speed-kmh 500
python -m soc_toolkit --help
```

### Example output

Running the first command against the synthetic sample data flags one pair of logins:

```
========================================================================
SOC Investigation Toolkit v0.1.0 - Impossible Travel Analysis
========================================================================
Input file       : data/sample/synthetic_logins.csv
Login events     : 12
Users analysed   : 5
Login pairs      : 7
Speed threshold  : 900.0 km/h (source: built-in default)
Pairs flagged    : 1

------------------------------------------------------------------------
FINDING 1 of 1: Impossible travel - REQUIRES ANALYST INVESTIGATION
------------------------------------------------------------------------
User             : bob@example.com
Previous login   : 2026-03-02 09:00:00 UTC | 192.0.2.20 | London, GB (51.5074, -0.1278) [row 8]
Current login    : 2026-03-02 11:00:00 UTC | 203.0.113.25 | Sydney, AU (-33.8688, 151.2093) [row 2]
Distance         : 16,994.0 km
Elapsed time     : 2h 00m 00s
Required speed   : 8,497.0 km/h (threshold 900.0 km/h)

Suggested analyst checks:
  - Confirm with the user (via a trusted channel) whether they made both sign-ins.
  - Check whether either IP belongs to a corporate VPN, proxy or cloud egress range.
  - Review both sign-ins in the source logs: MFA result, device, client and user agent.
  - Look for follow-on activity from the second IP (mailbox rules, token use, data access).

========================================================================
IMPORTANT: This output is automated investigation support, NOT a determination
of compromise. Every finding requires analyst investigation and verification
against the original log sources before any conclusion or response action.

Known limitations:
  - IP geolocation can be inaccurate, especially for mobile and ISP-assigned IPs.
  - VPNs, proxies, and cloud services can place a legitimate user far from their real location.
  - Only consecutive logins present in the input file are compared.
  - Distances are great-circle estimates; required speeds are approximate minimums.
  - Values are reported as provided in the input and have not been independently verified.
========================================================================
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

The input is a UTF-8 CSV file with a header row and these columns (extra columns are ignored; duplicate column names are rejected):

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

### How the modules fit together

`cli.py` runs each stage in order:

```
1. config.py             choose the threshold: --max-speed-kmh > --config file > built-in default
2. loader.py             read the CSV, validate every row, convert timestamps to UTC
3. impossible_travel.py  pair each user's consecutive logins, calculate speed, flag
     └─ geo.py           haversine distance between the two logins
4. report.py             format the SOC-style text report
```

`cli.py` then prints the report (exit code 0). If any stage finds invalid input or configuration, it prints an error instead and produces no report (exit code 1).

The stages pass data to each other as the read-only records defined in `models.py` (`LoginEvent` and `TravelAssessment`). `impossible_travel.py`, `geo.py` and `report.py` never read files or print, so they are unit-tested with in-memory data. Only `cli.py` prints.

## Limitations

The toolkit only compares the values in the input file. Every finding must be verified by an analyst.

### Common causes of false positives

- **VPNs, proxies and cloud services** can place a legitimate user far from their real location, and a user may switch between a VPN and a direct connection within minutes.
- **Inaccurate IP geolocation**, especially for mobile carrier and ISP-assigned addresses, which often geolocate to a regional hub hundreds of kilometres from the user.
- **Short distances with coarse geolocation.** Two logins 10 minutes apart that geolocate 200 km apart require 1,200 km/h and are flagged, even if the user never moved. Version 0.1 has no minimum-distance tolerance.
- **Clock skew** between log sources can shrink the apparent time between two logins and inflate the required speed.

### False negatives (activity that is not flagged)

- **Nearby VPN or proxy exits.** An attacker connecting through a VPN or proxy close to the user's real location produces no impossible travel.
- **Logins missing from the input file.** Only consecutive logins *in the file* are compared. If an export leaves out a log source or a time range, the suspicious login may not be there at all, or its nearest login in the file may be far enough away in time that the required speed looks plausible.
- **One account under different identifiers.** Users are matched by name, case-insensitively, so the same account recorded as a UPN in one source and as `DOMAIN\user` in another is treated as two users, and those logins are never paired.
- **Compromise without travel.** A stolen session token used from near the user's location, for example, produces no travel anomaly at all.

### Accuracy

- Distances are great-circle estimates, so required speeds are approximate minimums based on the input coordinates.
- Input values are trusted as provided. The toolkit does not look up or verify IP locations.

## Responsible use

This is a defensive project, built to help SOC analysts triage alerts on systems they are authorised to monitor.

- Only analyse authentication logs you are authorised to access, and handle them under your organisation's data-protection and retention policies.
- Login times and locations are personal data. Use the toolkit for legitimate security investigation, not to track individuals' movements or working patterns.
- Never commit real user, IP or sign-in data to this repository or a fork. Use synthetic data for demonstrations.
- Findings are leads for investigation, not evidence of wrongdoing. Do not take action against a user based on this output alone.

## Scope

Version 0.1 deliberately excludes Azure, Microsoft Sentinel/KQL, PowerShell, external or enrichment APIs, databases, and web or AI features. These are planned for later versions.

## Development notes

This project was built with AI assistance (Claude Code). [CLAUDE.md](CLAUDE.md) contains the project rules and security requirements the assistant worked under.

## License

Released under the MIT License. See [LICENSE](LICENSE).
