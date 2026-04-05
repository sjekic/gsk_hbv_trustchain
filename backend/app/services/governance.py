from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..models import AccessAudit, Consent, Permit
from ..security import AuthenticatedUser

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


def _date_is_active(until_value: str | None) -> bool:
    if not until_value:
        return True
    try:
        return date.fromisoformat(until_value) >= date.today()
    except ValueError:
        return False


def _consent_to_dict(c: Consent) -> dict[str, Any]:
    return {
        "id": c.id,
        "created_at": c.created_at,
        "created_by": c.created_by,
        "patient_pseudonym": c.patient_pseudonym,
        "legal_basis": c.legal_basis,
        "article_9_condition": c.article_9_condition,
        "purpose": c.purpose,
        "status": c.status,
        "retention_until": c.retention_until,
        "residency_region": c.residency_region,
        "notes": c.notes,
    }


def _permit_to_dict(p: Permit) -> dict[str, Any]:
    d = {
        "id": p.id,
        "created_at": p.created_at,
        "created_by": p.created_by,
        "permit_id": p.permit_id,
        "requesting_organization": p.requesting_organization,
        "purpose_code": p.purpose_code,
        "expiry_date": p.expiry_date,
        "issuing_hdab": p.issuing_hdab,
        "notes": p.notes,
        "status": p.status,
    }
    if d["status"] == "active" and not _date_is_active(d.get("expiry_date")):
        d["status"] = "expired"
    return d


def _audit_to_dict(a: AccessAudit) -> dict[str, Any]:
    roles = a.roles
    if isinstance(roles, str):
        try:
            roles = json.loads(roles)
        except (json.JSONDecodeError, TypeError):
            roles = [roles]
    return {
        "id": a.id,
        "timestamp": a.timestamp,
        "username": a.username,
        "roles": roles,
        "action": a.action,
        "resource_type": a.resource_type,
        "resource_id": a.resource_id,
        "decision": a.decision,
        "detail": a.detail,
        "permit_id": a.permit_id,
    }


def list_consents(db: Session) -> list[dict[str, Any]]:
    rows = db.query(Consent).order_by(Consent.created_at.desc()).all()
    return [_consent_to_dict(r) for r in rows]


def list_access_audit(db: Session) -> list[dict[str, Any]]:
    rows = db.query(AccessAudit).order_by(AccessAudit.timestamp.desc()).all()
    return [_audit_to_dict(r) for r in rows]


def has_active_governance_record_for_pseudonym(db: Session, patient_pseudonym: str) -> bool:
    rows = db.query(Consent).filter(
        Consent.patient_pseudonym == patient_pseudonym,
        Consent.status == "active",
    ).all()
    for record in rows:
        if _date_is_active(record.retention_until):
            return True
    return False


def create_consent_record(
    db: Session,
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
    row = Consent(
        id=uuid.uuid4().hex[:12],
        created_at=_now_iso(),
        created_by=user.username,
        patient_pseudonym=patient_pseudonym.strip(),
        legal_basis=legal_basis.strip(),
        article_9_condition=article_9_condition.strip(),
        purpose=purpose.strip(),
        status=status.strip(),
        retention_until=retention_until.strip() if retention_until else None,
        residency_region=residency_region.strip(),
        notes=notes.strip(),
    )
    db.add(row)
    db.flush()
    return _consent_to_dict(row)


def list_permits(db: Session) -> list[dict[str, Any]]:
    rows = db.query(Permit).order_by(Permit.created_at.desc()).all()
    return [_permit_to_dict(r) for r in rows]


def create_permit_record(
    db: Session,
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

    row = Permit(
        id=uuid.uuid4().hex[:12],
        created_at=_now_iso(),
        created_by=user.username,
        permit_id=permit_id.strip(),
        requesting_organization=requesting_organization.strip(),
        purpose_code=normalized_purpose,
        expiry_date=expiry_date.strip(),
        issuing_hdab=issuing_hdab.strip() or "Simulated HDAB",
        status="active",
        notes=notes.strip(),
    )
    db.add(row)
    db.flush()
    return _permit_to_dict(row)


def get_active_permit(db: Session) -> dict[str, Any] | None:
    permits = list_permits(db)
    for permit in permits:
        if permit["status"] != "active":
            continue
        if not _date_is_active(permit.get("expiry_date")):
            continue
        return permit
    return None


def log_access_event(
    db: Session,
    *,
    user: AuthenticatedUser,
    action: str,
    resource_type: str,
    resource_id: str,
    decision: str,
    detail: str = "",
    permit_id: str | None = None,
) -> dict[str, Any]:
    row = AccessAudit(
        id=uuid.uuid4().hex[:12],
        timestamp=_now_iso(),
        username=user.username,
        roles=json.dumps(user.roles),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        decision=decision,
        detail=detail.strip(),
        permit_id=permit_id,
    )
    db.add(row)
    db.flush()
    return _audit_to_dict(row)
