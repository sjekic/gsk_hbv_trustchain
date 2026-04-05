"""HBV-specific quality rules executed after OMOP loading."""

from dataclasses import dataclass


@dataclass
class DQIssue:
    code: str
    severity: str
    summary: str


def validate_hbv_panel(record: dict) -> list[DQIssue]:
    issues: list[DQIssue] = []
    alt = record.get("alt_value")
    hbsag = record.get("hbsag_quantitative_value")
    hbv_dna = record.get("hbv_dna_quantitative_value")

    if record.get("bepirovirsen_flag") and hbsag is None:
        issues.append(DQIssue("HBV001", "high", "Missing baseline HBsAg for bepirovirsen-treated patient"))

    if record.get("functional_cure_flag") and hbv_dna not in (0, None) and record.get("hbv_dna_detectable_flag"):
        issues.append(DQIssue("HBV002", "critical", "Functional cure flagged while HBV DNA remains detectable"))

    if alt is not None and alt < 0:
        issues.append(DQIssue("HBV003", "high", "ALT cannot be negative"))

    return issues
