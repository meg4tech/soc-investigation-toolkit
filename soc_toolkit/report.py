"""SOC-style text report for Impossible Travel results.

The report only states values derived from the input file. The suggested
checks are generic guidance for the analyst, not evidence or conclusions.
"""

from pathlib import Path

from . import __version__
from .config import DetectionConfig
from .models import LoginEvent, TravelAssessment

RULE = "=" * 72
DIVIDER = "-" * 72

SUGGESTED_CHECKS = (
    "Confirm with the user (via a trusted channel) whether they made both sign-ins.",
    "Check whether either IP belongs to a corporate VPN, proxy or cloud egress range.",
    "Review both sign-ins in the source logs: MFA result, device, client and user agent.",
    "Look for follow-on activity from the second IP (mailbox rules, token use, data access).",
)

ANALYST_NOTICE = (
    "IMPORTANT: This output is automated investigation support, NOT a determination",
    "of compromise. Every finding requires analyst investigation and verification",
    "against the original log sources before any conclusion or response action.",
)

LIMITATIONS = (
    "IP geolocation can be inaccurate, especially for mobile and ISP-assigned IPs.",
    "VPNs, proxies, and cloud services can place a legitimate user far from their real location.",
    "Only consecutive logins present in the input file are compared.",
    "Distances are great-circle estimates; required speeds are approximate minimums.",
    "Values are reported as provided in the input and have not been independently verified.",
)


def format_report(
    events: list[LoginEvent],
    assessments: list[TravelAssessment],
    config: DetectionConfig,
    input_path: str | Path,
) -> str:
    flagged = [a for a in assessments if a.flagged]
    users = {event.user for event in events}

    lines = [
        RULE,
        f"SOC Investigation Toolkit v{__version__} - Impossible Travel Analysis",
        RULE,
        f"Input file       : {input_path}",
        f"Login events     : {len(events)}",
        f"Users analysed   : {len(users)}",
        f"Login pairs      : {len(assessments)}",
        f"Speed threshold  : {config.max_speed_kmh:,.1f} km/h (source: {config.source})",
        f"Pairs flagged    : {len(flagged)}",
        "",
    ]

    if flagged:
        for number, assessment in enumerate(flagged, start=1):
            lines.extend(_format_finding(assessment, number, len(flagged)))
    else:
        lines.extend([
            DIVIDER,
            "No login pairs exceeded the speed threshold.",
            "This does not rule out account compromise; it only means no consecutive",
            "logins in this file required implausible travel.",
            "",
        ])

    lines.append(RULE)
    lines.extend(ANALYST_NOTICE)
    lines.append("")
    lines.append("Known limitations:")
    lines.extend(f"  - {item}" for item in LIMITATIONS)
    lines.append(RULE)
    return "\n".join(lines)


def _format_finding(assessment: TravelAssessment, number: int, total: int) -> list[str]:
    lines = [
        DIVIDER,
        f"FINDING {number} of {total}: Impossible travel - REQUIRES ANALYST INVESTIGATION",
        DIVIDER,
        f"User             : {assessment.user}",
        f"Previous login   : {_format_login(assessment.previous)}",
        f"Current login    : {_format_login(assessment.current)}",
        f"Distance         : {assessment.distance_km:,.1f} km",
        f"Elapsed time     : {_format_elapsed(assessment.elapsed_seconds)}",
        f"Required speed   : {assessment.speed_kmh:,.1f} km/h "
        f"(threshold {assessment.threshold_kmh:,.1f} km/h)",
        "",
        "Suggested analyst checks:",
    ]
    lines.extend(f"  - {check}" for check in SUGGESTED_CHECKS)
    lines.append("")
    return lines


def _format_login(event: LoginEvent) -> str:
    timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        f"{timestamp} | {event.ip_address} | {event.location} "
        f"({event.latitude:.4f}, {event.longitude:.4f}) [row {event.source_row}]"
    )


def _format_elapsed(seconds: float) -> str:
    total = round(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}h {minutes:02d}m {secs:02d}s"
