from fastapi import APIRouter, Query

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/cohort")
def cohort_summary(country: str | None = None, bepirovirsen_only: bool = Query(False)):
    return {
        "filters": {"country": country, "bepirovirsen_only": bepirovirsen_only},
        "counts": {
            "hbv_patients": 1248,
            "bepirovirsen_patients": 112 if bepirovirsen_only else 112,
            "linked_across_two_or_more_sources": 917,
        },
        "metrics": {
            "hbsag_completeness": 0.91,
            "hbv_dna_completeness": 0.93,
            "alt_completeness": 0.96,
        },
    }


@router.get("/{person_id}/journey")
def patient_journey(person_id: int):
    return {
        "person_id": person_id,
        "timeline": [
            {"date": "2025-01-10", "event": "CHB confirmed"},
            {"date": "2025-02-05", "event": "NA therapy ongoing"},
            {"date": "2025-07-01", "event": "Bepirovirsen started"},
        ],
        "labs": {
            "hbsag": [{"date": "2025-07-01", "value": 120.0}, {"date": "2025-10-01", "value": 8.4}],
            "hbv_dna": [{"date": "2025-07-01", "value": 2300.0}, {"date": "2025-10-01", "value": 0.0}],
            "alt": [{"date": "2025-07-01", "value": 74.0}, {"date": "2025-10-01", "value": 34.0}],
        },
        "alerts": ["Verify sustained HBsAg loss at next follow-up"],
    }
