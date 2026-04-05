"""Example source-to-OMOP mapping helpers for HBV data."""

from dataclasses import dataclass
from typing import Any


@dataclass
class MeasurementRecord:
    person_id: int
    measurement_concept: str
    measurement_date: str
    value_as_number: float | None
    unit_source_value: str | None
    value_source_value: str | None


LAB_MAP = {
    "HBsAg": "HBsAg quantitative",
    "HBV_DNA": "HBV DNA quantitative",
    "ALT": "ALT",
    "AST": "AST",
    "HBeAg": "HBeAg status",
    "BILIRUBIN": "Bilirubin",
    "ALBUMIN": "Albumin",
    "INR": "INR",
}


def map_lab_row(row: dict[str, Any], person_id: int) -> MeasurementRecord:
    analyte = row.get("analyte_code")
    return MeasurementRecord(
        person_id=person_id,
        measurement_concept=LAB_MAP.get(analyte, "UNKNOWN"),
        measurement_date=str(row.get("collection_date")),
        value_as_number=row.get("numeric_value"),
        unit_source_value=row.get("unit"),
        value_source_value=str(row.get("raw_result")),
    )
