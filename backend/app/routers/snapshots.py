from fastapi import APIRouter

router = APIRouter(prefix="/snapshots", tags=["snapshots"])


@router.get("")
def list_snapshots():
    return {
        "items": [
            {
                "snapshot_id": "demo-snapshot-001",
                "snapshot_label": "HBV OMOP Snapshot 2026-04",
                "omop_release_date": "2026-04-01",
                "cdm_version": "5.4",
                "etl_version": "etl-0.1.0",
                "status": "validated",
            }
        ]
    }
