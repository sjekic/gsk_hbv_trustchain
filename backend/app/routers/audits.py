from fastapi import APIRouter

router = APIRouter(prefix="/audits", tags=["audits"])


@router.get("/provenance/{snapshot_id}")
def provenance(snapshot_id: str):
    return {
        "snapshot_id": snapshot_id,
        "manifest_sha256": "9fb6...demo",
        "fabric_channel": "hbv-provenance",
        "tx_id": "fabric-tx-demo-001",
        "verification_status": "verified",
        "events": [
            {"step": "landing_registered", "at": "2026-04-01T09:00:00Z"},
            {"step": "omop_snapshot_created", "at": "2026-04-01T09:20:00Z"},
            {"step": "dq_completed", "at": "2026-04-01T09:35:00Z"},
            {"step": "ledger_notarized", "at": "2026-04-01T09:37:00Z"},
        ],
    }
