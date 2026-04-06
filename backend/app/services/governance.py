from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from ..security import AuthenticatedUser

STORE_DIR = Path(__file__).resolve().parents[2] / "data"
STORE_PATH = STORE_DIR / "prototype_store.json"
STORE_LOCK = Lock()

PERMIT_PURPOSE_CODES = {
    "research",
    "innovation",
    "policy_making",
    "patient_safety",
    "personalized_medicine",
    "official_statistics",
    "regulatory",
    "health_threat_preparedness",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_store(store: dict[str, Any]) -> dict[str, Any]:
    if "submissions" not in store:
        store["submissions"] = []
    if "ledger" not in store:
        store["ledger"] = []
    if "patients" not in store:
        store["patients"] = []
    if "consents" not in store:
        store["consents"] = []
    if "access_audit" not in store:
        store["access_audit"] = []
    if "permits" not in store:
        store["permits"] = []

    for patient in store["patients"]:
        if "visits" not in patient:
            patient["visits"] = []

    return store


def _ensure_store_exists() -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        STORE_PATH.write_text(
            json.dumps(
                {
                    "submissions": [],
                    "ledger": [],
                    "patients": [],
                    "consents": [],
                    "access_audit": [],
                    "permits": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def _load_store() -> dict[str, Any]:
    _ensure_store_exists()
    with STORE_LOCK:
        store = json.loads(STORE_PATH.read_text(encoding="utf-8"))
        return _normalize_store(store)


def _save_store(store: dict[str, Any]) -> None:
    _ensure_store_exists()
    with STORE_LOCK:
        STORE_PATH.write_text(json.dumps(_normalize_store(store), indent=2), encoding="utf-8")


def list_consents() -> list[dict[str, Any]]:
    store = _load_store()
    return sorted(store["consents"], key=lambda item: item["created_at"], reverse=True)


def list_access_audit() -> list[dict[str, Any]]:
    store = _load_store()
    return sorted(store["access_audit"], key=lambda item: item["timestamp"], reverse=True)


def _date_is_active(until_value: str | None) -> bool:
    if not until_value:
        return True
    try:
        return date.fromisoformat(until_value) >= date.today()
    except ValueError:
        return False


def has_active_governance_record_for_pseudonym(patient_pseudonym: str) -> bool:
    store = _load_store()
    for record in store["consents"]:
        if record["patient_pseudonym"] != patient_pseudonym:
            continue
        if record["status"] != "active":
            continue
        if not _date_is_active(record.get("retention_until")):
            continue
        return True
    return False


def create_consent_record(
    *,
    user: AuthenticatedUser,
    patient_pseudonym: str,
    legal_basis: str,
    article_9_condition: str,
    purpose: str,
    status: str,
    retention_until: str | None,
    residency_region: str,
    notes: str,
) -> dict[str, Any]:
    store = _load_store()
    record = {
        "id": uuid.uuid4().hex[:12],
        "created_at": _now_iso(),
        "created_by": user.username,
        "patient_pseudonym": patient_pseudonym.strip(),
        "legal_basis": legal_basis.strip(),
        "article_9_condition": article_9_condition.strip(),
        "purpose": purpose.strip(),
        "status": status.strip(),
        "retention_until": retention_until.strip() if retention_until else None,
        "residency_region": residency_region.strip(),
        "notes": notes.strip(),
    }
    store["consents"].append(record)
    _save_store(store)
    return record


def list_permits() -> list[dict[str, Any]]:
    store = _load_store()
    permits = []
    for permit in store["permits"]:
        permit_copy = dict(permit)
        if permit_copy["status"] == "active" and not _date_is_active(permit_copy.get("expiry_date")):
            permit_copy["status"] = "expired"
        permits.append(permit_copy)
    return sorted(permits, key=lambda item: item["created_at"], reverse=True)


def create_permit_record(
    *,
    user: AuthenticatedUser,
    permit_id: str,
    requesting_organization: str,
    purpose_code: str,
    expiry_date: str,
    issuing_hdab: str,
    notes: str,
) -> dict[str, Any]:
    normalized_purpose = purpose_code.strip()
    if normalized_purpose not in PERMIT_PURPOSE_CODES:
        raise ValueError(
            f"Invalid purpose_code '{normalized_purpose}'. "
            f"Allowed values: {', '.join(sorted(PERMIT_PURPOSE_CODES))}"
        )

    store = _load_store()
    record = {
        "id": uuid.uuid4().hex[:12],
        "created_at": _now_iso(),
        "created_by": user.username,
        "permit_id": permit_id.strip(),
        "requesting_organization": requesting_organization.strip(),
        "purpose_code": normalized_purpose,
        "expiry_date": expiry_date.strip(),
        "issuing_hdab": issuing_hdab.strip() or "Simulated HDAB",
        "status": "active",
        "notes": notes.strip(),
    }
    store["permits"].append(record)
    _save_store(store)
    return record


def get_active_permit() -> dict[str, Any] | None:
    permits = list_permits()
    for permit in permits:
        if permit["status"] != "active":
            continue
        if not _date_is_active(permit.get("expiry_date")):
            continue
        return permit
    return None


def log_access_event(
    *,
    user: AuthenticatedUser,
    action: str,
    resource_type: str,
    resource_id: str,
    decision: str,
    detail: str = "",
    permit_id: str | None = None,
) -> dict[str, Any]:
    store = _load_store()
    event = {
        "id": uuid.uuid4().hex[:12],
        "timestamp": _now_iso(),
        "username": user.username,
        "roles": user.roles,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "decision": decision,
        "detail": detail.strip(),
        "permit_id": permit_id,
    }
    store["access_audit"].append(event)
    _save_store(store)
    return event