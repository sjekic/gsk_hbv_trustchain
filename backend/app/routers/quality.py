from fastapi import APIRouter

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/overview")
def quality_overview():
    return {
        "overall_score": 94.2,
        "critical_issues": 2,
        "checks": {
            "completeness": 95.1,
            "conformance": 98.0,
            "plausibility": 91.8,
            "temporal": 92.4,
        },
    }
