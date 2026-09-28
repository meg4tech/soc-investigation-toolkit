# Sample data: SYNTHETIC ONLY

Every file in this directory is **synthetic**. None of it came from a real system.

- Users are on `example.com`, a domain reserved for documentation (RFC 2606).
- IP addresses are from the documentation ranges `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24` (RFC 5737) and `2001:db8::/32` (RFC 3849). They are reserved for documentation and should never be routed on the public internet.
- Coordinates are approximate city centres.

Never replace these files with real authentication logs, and never commit real user, IP or sign-in data to this repository. Sample files must keep the `synthetic_` filename prefix. `.gitignore` excludes any other file in `data/`.

## Scenarios in `synthetic_logins.csv`

Rows are deliberately out of order and interleaved across users, to exercise sorting and per-user grouping.

| User | Scenario | Expected result |
|---|---|---|
| alice | London → Paris (5.5 h later) → Paris next day | Not flagged |
| bob | London → Sydney 2 hours later | **Flagged** (~8,500 km/h) |
| carol | Single login | No pairs to assess |
| dave | New York → London overnight (~655 km/h) → Manchester | Not flagged (realistic flight) |
| erin | Duplicate Madrid event, then Barcelona | Duplicate is 0 km/h; not flagged |

dave's New York timestamp uses a `-05:00` offset, and carol's uses `Z`. This shows that timestamps in different timezones are compared correctly.
