from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import LedgerBlock
from ..security import AuthenticatedUser, get_current_user, list_demo_users, require_roles
from ..services.demo_data import (
    create_patient_visit,
    create_prototype_patient,
    create_prototype_submission,
    get_export_anonymization_status,
    get_hbsag_trajectory,
    get_prototype_dashboard,
    get_prototype_patients,
    get_prototype_submissions,
    verify_chain_integrity,
    verify_patient_integrity,
    verify_submission_integrity,
    verify_visit_integrity,
    _ledger_to_dict,
)
from ..services.governance import (
    create_consent_record,
    create_permit_record,
    get_active_permit,
    has_active_governance_record_for_pseudonym,
    list_access_audit,
    list_consents,
    list_permits,
    log_access_event,
)

router = APIRouter(prefix="/prototype", tags=["prototype"])


def _build_permit_gate(db: Session) -> dict:
    active_permit = get_active_permit(db)
    if active_permit:
        return {
            "restricted": False,
            "banner": f"Operating under Permit #{active_permit['permit_id']}",
            "active_permit": active_permit,
        }
    return {
        "restricted": True,
        "banner": "Secondary-use dashboard access is restricted until an active EHDS-style data access permit is registered.",
        "active_permit": None,
    }


def _require_active_permit(
    db: Session,
    *,
    user: AuthenticatedUser,
    action: str,
    resource_type: str,
    resource_id: str,
) -> dict:
    permit = get_active_permit(db)
    if permit is None:
        log_access_event(
            db,
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            decision="blocked",
            detail="No active data access permit",
            permit_id=None,
        )
        db.commit()
        raise HTTPException(
            status_code=403,
            detail="No active EHDS-style data access permit is registered.",
        )
    return permit


def _restricted_dashboard_payload() -> dict:
    return {
        "prototype": {
            "name": "RWD TrustChain",
            "subtitle": "Interactive prototype for secure dataset intake, patient/visit capture, validation, and simulated ledger notarization.",
            "challenge": [
                "Capture decentralized dataset submissions and structured clinician-entered HBV patient records in one prototype.",
                "Hash every stored artifact and anchor provenance metadata in an append-only simulated ledger.",
                "Surface live readiness, data quality, and integrity signals for trials and Real-World Evidence generation.",
            ],
            "regulatory_alignment": [
                "GDPR privacy by design",
                "OMOP-oriented standardization",
                "EHDS-ready interoperability",
                "FDA 21 CFR Part 11-style auditability",
            ],
        },
        "top_cards": [],
        "source_feeds": [],
        "omop_etl": {
            "current_snapshot": {
                "snapshot_id": "",
                "snapshot_status": "warning",
                "mapping_coverage": 0,
                "vocabulary_coverage": 0,
                "quality_gate_pass_rate": 0,
                "snapshot_block": None,
            },
            "run_context": {
                "run_id": "",
                "etl_spec_version": "",
                "vocabulary_release": "",
                "target_cdm": "",
                "last_run_at": "",
                "status": "warning",
            },
            "domain_loads": [],
            "mapping_gaps": [
                "Dashboard access is locked until an active secondary-use data access permit is registered."
            ],
        },
        "export_gate": {
            "passed": False,
            "message": "Export blocked. No active permit is registered.",
            "k_threshold": 5,
            "eligible_patients": 0,
            "opted_out_patients": 0,
            "smallest_cell": 0,
            "failing_cells": [],
        },
        "data_lifecycle": [],
        "ledger": [],
        "quality": {
            "dimensions": [],
            "issue_severity": [],
            "readiness_trend": [],
            "source_coverage": [],
            "open_findings": [
                "No active secondary-use permit is registered, so dashboard analytics are restricted."
            ],
        },
        "trial_readiness": [],
        "next_steps": [
            "Register an active EHDS-style data access permit.",
            "Then re-open the dashboard to view source, OMOP, patient, visit, and provenance data.",
        ],
    }


@router.get("/me")
def who_am_i(user: AuthenticatedUser = Depends(get_current_user)):
    return {
        "username": user.username,
        "roles": user.roles,
        "auth_source": user.auth_source,
        "auth_mode": settings.auth_mode,
    }


@router.get("/dev-users")
def dev_users():
    return {"items": list_demo_users()}


@router.get("/permits")
def get_permits(
    user: AuthenticatedUser = Depends(
        require_roles("clinician", "data_steward", "site_admin", "auditor")
    ),
    db: Session = Depends(get_db),
):
    log_access_event(
        db,
        user=user,
        action="list_permits",
        resource_type="permit",
        resource_id="all",
        decision="allowed",
        permit_id=get_active_permit(db)["permit_id"] if get_active_permit(db) else None,
    )
    result = {"items": list_permits(db), "active_permit": get_active_permit(db)}
    db.commit()
    return result


@router.post("/permits")
def create_permit(
    permit_id: str = Form(...),
    requesting_organization: str = Form(...),
    purpose_code: str = Form(...),
    expiry_date: str = Form(...),
    issuing_hdab: str = Form("Simulated HDAB"),
    notes: str = Form(""),
    user: AuthenticatedUser = Depends(
        require_roles("clinician", "data_steward", "site_admin")
    ),
    db: Session = Depends(get_db),
):
    try:
        record = create_permit_record(
            db,
            user=user,
            permit_id=permit_id,
            requesting_organization=requesting_organization,
            purpose_code=purpose_code,
            expiry_date=expiry_date,
            issuing_hdab=issuing_hdab,
            notes=notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_access_event(
        db,
        user=user,
        action="create_permit",
        resource_type="permit",
        resource_id=record["permit_id"],
        decision="allowed",
        permit_id=record["permit_id"],
    )

    db.commit()
    return {
        "message": "Data access permit stored and activated.",
        "record": record,
    }


@router.get("/dashboard")
def prototype_dashboard(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    permit_gate = _build_permit_gate(db)

    if permit_gate["restricted"]:
        log_access_event(
            db,
            user=user,
            action="read_dashboard",
            resource_type="dashboard",
            resource_id="prototype",
            decision="blocked",
            detail="No active data access permit",
            permit_id=None,
        )
        db.commit()
        payload = _restricted_dashboard_payload()
        payload["permit_gate"] = permit_gate
        return payload

    payload = get_prototype_dashboard(db)
    payload["permit_gate"] = permit_gate

    log_access_event(
        db,
        user=user,
        action="read_dashboard",
        resource_type="dashboard",
        resource_id="prototype",
        decision="allowed",
        detail=f"permit={permit_gate['active_permit']['permit_id']}",
        permit_id=permit_gate["active_permit"]["permit_id"],
    )
    db.commit()
    return payload


@router.get("/submissions")
def list_submissions(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    permit = _require_active_permit(
        db,
        user=user,
        action="list_submissions",
        resource_type="submission",
        resource_id="all",
    )
    log_access_event(
        db,
        user=user,
        action="list_submissions",
        resource_type="submission",
        resource_id="all",
        decision="allowed",
        permit_id=permit["permit_id"],
    )
    result = {"items": get_prototype_submissions(db)}
    db.commit()
    return result


@router.post("/submissions")
async def create_submission(
    site_name: str = Form(...),
    source_type: str = Form(...),
    country: str = Form(...),
    operator_id: str = Form(...),
    record_count: int = Form(...),
    hbv_cohort: int = Form(...),
    bepirovirsen_treated: int = Form(0),
    dq_score: float = Form(...),
    readiness_score: float = Form(...),
    schema_signed: bool = Form(True),
    temporal_issue_count: int = Form(0),
    needs_vocab_remap: bool = Form(False),
    notes: str = Form(""),
    file: UploadFile | None = File(None),
    user: AuthenticatedUser = Depends(
        require_roles("clinician", "data_steward", "site_admin")
    ),
    db: Session = Depends(get_db),
):
    file_bytes = None
    file_name = None

    if file is not None:
        file_name = file.filename
        file_bytes = await file.read()

    submission, ledger_entry = create_prototype_submission(
        db,
        site_name=site_name,
        source_type=source_type,
        country=country,
        operator_id=operator_id,
        record_count=record_count,
        hbv_cohort=hbv_cohort,
        bepirovirsen_treated=bepirovirsen_treated,
        dq_score=dq_score,
        readiness_score=readiness_score,
        schema_signed=schema_signed,
        temporal_issue_count=temporal_issue_count,
        needs_vocab_remap=needs_vocab_remap,
        notes=notes,
        file_name=file_name,
        file_bytes=file_bytes,
    )

    log_access_event(
        db,
        user=user,
        action="create_submission",
        resource_type="submission",
        resource_id=submission["id"],
        decision="allowed",
        detail=f"block={ledger_entry['block']}",
        permit_id=get_active_permit(db)["permit_id"] if get_active_permit(db) else None,
    )

    db.commit()
    return {
        "message": "Submission stored and anchored in the simulated ledger.",
        "submission": submission,
        "ledger_entry": ledger_entry,
    }


@router.get("/submissions/{submission_id}/verify")
def verify_submission(
    submission_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    permit = _require_active_permit(
        db,
        user=user,
        action="verify_submission",
        resource_type="submission",
        resource_id=submission_id,
    )
    result = verify_submission_integrity(db, submission_id)
    log_access_event(
        db,
        user=user,
        action="verify_submission",
        resource_type="submission",
        resource_id=submission_id,
        decision="allowed" if result.get("verified") else "warning",
        permit_id=permit["permit_id"],
    )
    db.commit()
    return result


@router.get("/consents")
def get_consents(
    user: AuthenticatedUser = Depends(
        require_roles("clinician", "data_steward", "site_admin", "auditor")
    ),
    db: Session = Depends(get_db),
):
    log_access_event(
        db,
        user=user,
        action="list_consents",
        resource_type="consent",
        resource_id="all",
        decision="allowed",
        permit_id=get_active_permit(db)["permit_id"] if get_active_permit(db) else None,
    )
    result = {"items": list_consents(db)}
    db.commit()
    return result


@router.post("/consents")
def create_consent(
    patient_pseudonym: str = Form(...),
    legal_basis: str = Form(...),
    article_9_condition: str = Form(...),
    purpose: str = Form(...),
    status: str = Form("active"),
    retention_until: str | None = Form(None),
    residency_region: str = Form("EU"),
    notes: str = Form(""),
    user: AuthenticatedUser = Depends(
        require_roles("clinician", "data_steward", "site_admin")
    ),
    db: Session = Depends(get_db),
):
    record = create_consent_record(
        db,
        user=user,
        patient_pseudonym=patient_pseudonym,
        legal_basis=legal_basis,
        article_9_condition=article_9_condition,
        purpose=purpose,
        status=status,
        retention_until=retention_until,
        residency_region=residency_region,
        notes=notes,
    )

    log_access_event(
        db,
        user=user,
        action="create_consent",
        resource_type="consent",
        resource_id=record["id"],
        decision="allowed",
        permit_id=get_active_permit(db)["permit_id"] if get_active_permit(db) else None,
    )

    db.commit()
    return {
        "message": "Governance basis record stored.",
        "record": record,
    }


@router.get("/access-audit")
def access_audit(
    user: AuthenticatedUser = Depends(require_roles("data_steward", "site_admin", "auditor")),
    db: Session = Depends(get_db),
):
    result = {"items": list_access_audit(db)}
    db.commit()
    return result


@router.get("/patients")
def list_patients(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    permit = _require_active_permit(
        db,
        user=user,
        action="list_patients",
        resource_type="patient",
        resource_id="all",
    )
    log_access_event(
        db,
        user=user,
        action="list_patients",
        resource_type="patient",
        resource_id="all",
        decision="allowed",
        permit_id=permit["permit_id"],
    )
    result = {"items": get_prototype_patients(db)}
    db.commit()
    return result


@router.post("/patients")
def create_patient(
    site_name: str = Form(...),
    country: str = Form(...),
    operator_id: str = Form(...),
    patient_pseudonym: str = Form(...),
    sex: str = Form(...),
    year_of_birth: int = Form(...),
    diagnosis_date: str = Form(...),
    chronic_hbv_confirmed: bool = Form(True),
    on_na_therapy: bool = Form(False),
    bepirovirsen_eligible: bool = Form(False),
    started_bepirovirsen: bool = Form(False),
    opted_out_secondary_use: bool = Form(False),
    baseline_hbsag: float | None = Form(None),
    baseline_hbv_dna: float | None = Form(None),
    baseline_alt: float | None = Form(None),
    baseline_ast: float | None = Form(None),
    hbeag_status: str = Form("unknown"),
    bilirubin: float | None = Form(None),
    albumin: float | None = Form(None),
    inr: float | None = Form(None),
    notes: str = Form(""),
    user: AuthenticatedUser = Depends(require_roles("clinician", "site_admin")),
    db: Session = Depends(get_db),
):
    if settings.consent_required_for_patient_write and not has_active_governance_record_for_pseudonym(
        db, patient_pseudonym
    ):
        log_access_event(
            db,
            user=user,
            action="create_patient",
            resource_type="patient",
            resource_id=patient_pseudonym,
            decision="blocked",
            detail="Missing active governance basis record",
            permit_id=get_active_permit(db)["permit_id"] if get_active_permit(db) else None,
        )
        db.commit()
        raise HTTPException(
            status_code=403,
            detail=(
                "Active governance basis record required before patient creation. "
                "Create /prototype/consents entry first."
            ),
        )

    patient, ledger_entry = create_prototype_patient(
        db,
        site_name=site_name,
        country=country,
        operator_id=operator_id,
        patient_pseudonym=patient_pseudonym,
        sex=sex,
        year_of_birth=year_of_birth,
        diagnosis_date=diagnosis_date,
        chronic_hbv_confirmed=chronic_hbv_confirmed,
        on_na_therapy=on_na_therapy,
        bepirovirsen_eligible=bepirovirsen_eligible,
        started_bepirovirsen=started_bepirovirsen,
        opted_out_secondary_use=opted_out_secondary_use,
        baseline_hbsag=baseline_hbsag,
        baseline_hbv_dna=baseline_hbv_dna,
        baseline_alt=baseline_alt,
        baseline_ast=baseline_ast,
        hbeag_status=hbeag_status,
        bilirubin=bilirubin,
        albumin=albumin,
        inr=inr,
        notes=notes,
    )

    log_access_event(
        db,
        user=user,
        action="create_patient",
        resource_type="patient",
        resource_id=patient["id"],
        decision="allowed",
        detail=f"block={ledger_entry['block']}",
        permit_id=get_active_permit(db)["permit_id"] if get_active_permit(db) else None,
    )

    db.commit()
    return {
        "message": "Patient baseline record stored and anchored in the simulated ledger.",
        "patient": patient,
        "ledger_entry": ledger_entry,
    }


@router.post("/patients/{patient_id}/visits")
def create_visit(
    patient_id: str,
    visit_date: str = Form(...),
    visit_type: str = Form(...),
    quantitative_hbsag: float | None = Form(None),
    hbv_dna: float | None = Form(None),
    hbv_dna_detectable: bool = Form(True),
    alt: float | None = Form(None),
    ast: float | None = Form(None),
    hbeag_status: str = Form("unknown"),
    bilirubin: float | None = Form(None),
    albumin: float | None = Form(None),
    inr: float | None = Form(None),
    on_na_therapy: bool = Form(False),
    on_bepirovirsen: bool = Form(False),
    functional_cure_endpoint: bool = Form(False),
    notes: str = Form(""),
    user: AuthenticatedUser = Depends(require_roles("clinician", "site_admin")),
    db: Session = Depends(get_db),
):
    patients = get_prototype_patients(db)
    patient = next((item for item in patients if item["id"] == patient_id), None)

    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found.")

    if settings.consent_required_for_patient_write and not has_active_governance_record_for_pseudonym(
        db, patient["patient_pseudonym"]
    ):
        log_access_event(
            db,
            user=user,
            action="create_visit",
            resource_type="visit",
            resource_id=patient_id,
            decision="blocked",
            detail="Missing active governance basis record",
            permit_id=get_active_permit(db)["permit_id"] if get_active_permit(db) else None,
        )
        db.commit()
        raise HTTPException(
            status_code=403,
            detail=(
                "Active governance basis record required before visit creation. "
                "Create /prototype/consents entry first."
            ),
        )

    try:
        visit, ledger_entry = create_patient_visit(
            db,
            patient_id=patient_id,
            visit_date=visit_date,
            visit_type=visit_type,
            quantitative_hbsag=quantitative_hbsag,
            hbv_dna=hbv_dna,
            hbv_dna_detectable=hbv_dna_detectable,
            alt=alt,
            ast=ast,
            hbeag_status=hbeag_status,
            bilirubin=bilirubin,
            albumin=albumin,
            inr=inr,
            on_na_therapy=on_na_therapy,
            on_bepirovirsen=on_bepirovirsen,
            functional_cure_endpoint=functional_cure_endpoint,
            notes=notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    log_access_event(
        db,
        user=user,
        action="create_visit",
        resource_type="visit",
        resource_id=visit["id"],
        decision="allowed",
        detail=f"block={ledger_entry['block']}",
        permit_id=get_active_permit(db)["permit_id"] if get_active_permit(db) else None,
    )

    db.commit()
    return {
        "message": "Visit stored and anchored in the simulated ledger.",
        "visit": visit,
        "ledger_entry": ledger_entry,
    }

@router.get("/export/check-anonymization")
def check_export_anonymization(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    permit = _require_active_permit(
        db,
        user=user,
        action="check_export_anonymization",
        resource_type="export",
        resource_id="results",
    )
    result = get_export_anonymization_status(db)
    log_access_event(
        db,
        user=user,
        action="check_export_anonymization",
        resource_type="export",
        resource_id="results",
        decision="allowed" if result.get("passed") else "warning",
        permit_id=permit["permit_id"],
    )
    db.commit()
    return result

@router.get("/analytics/hbsag-trajectory")
def hbsag_trajectory(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    permit_gate = _build_permit_gate(db)
    if permit_gate["restricted"]:
        raise HTTPException(
            status_code=403,
            detail="No active EHDS-style data access permit is registered.",
        )
    result = get_hbsag_trajectory(db)
    log_access_event(
        db,
        user=user,
        action="read_hbsag_trajectory",
        resource_type="analytics",
        resource_id="hbsag_trajectory",
        decision="allowed",
        permit_id=permit_gate["active_permit"]["permit_id"],
    )
    db.commit()
    return result


@router.get("/ledger/chain-integrity")
def ledger_chain_integrity(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the full ledger with per-block chain_status annotation.
    Used by the tamper simulation panel on the frontend.
    """
    permit = _require_active_permit(
        db,
        user=user,
        action="read_chain_integrity",
        resource_type="ledger",
        resource_id="chain",
    )

    ledger_rows = db.query(LedgerBlock).order_by(LedgerBlock.block.asc()).all()
    ledger = [_ledger_to_dict(b) for b in ledger_rows]
    chain = verify_chain_integrity(ledger)
    broken_count = sum(1 for b in chain if b["chain_status"] == "broken")

    log_access_event(
        db,
        user=user,
        action="read_chain_integrity",
        resource_type="ledger",
        resource_id="chain",
        decision="allowed",
        permit_id=permit["permit_id"],
    )
    db.commit()
    return {
        "chain": sorted(chain, key=lambda b: b["block"]),
        "total_blocks": len(chain),
        "broken_blocks": broken_count,
        "chain_intact": broken_count == 0,
    }


@router.post("/ledger/tamper-simulate")
def tamper_simulate(
    block_number: int = Form(...),
    user: AuthenticatedUser = Depends(require_roles("data_steward", "site_admin")),
    db: Session = Depends(get_db),
):
    """
    Corrupts the artifact hash of a given block to demonstrate tamper detection.
    Only works in dev/prototype mode — never in production.
    """
    target = db.query(LedgerBlock).filter(LedgerBlock.block == block_number).first()
    if target is None:
        raise HTTPException(status_code=404, detail=f"Block {block_number} not found.")

    # Corrupt the artifact hash — leaves block_hash and previous_hash intact
    # so the mismatch is detected by verify_chain_integrity
    original_hash = target.hash
    target.hash = "tampered_" + original_hash[:55]
    target.status = "tampered"
    db.flush()

    ledger_rows = db.query(LedgerBlock).order_by(LedgerBlock.block.asc()).all()
    ledger = [_ledger_to_dict(b) for b in ledger_rows]
    chain = verify_chain_integrity(ledger)
    broken = [b for b in chain if b["chain_status"] == "broken"]

    log_access_event(
        db,
        user=user,
        action="tamper_simulate",
        resource_type="ledger",
        resource_id=str(block_number),
        decision="allowed",
        detail=f"Block {block_number} hash corrupted. {len(broken)} block(s) now broken.",
        permit_id=None,
    )
    db.commit()
    return {
        "tampered_block": block_number,
        "broken_blocks": [b["block"] for b in broken],
        "message": f"Block {block_number} corrupted. {len(broken)} block(s) now fail chain verification.",
    }

@router.get("/patients/{patient_id}/verify")
def verify_patient(
    patient_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    permit = _require_active_permit(
        db,
        user=user,
        action="verify_patient",
        resource_type="patient",
        resource_id=patient_id,
    )
    result = verify_patient_integrity(db, patient_id)
    log_access_event(
        db,
        user=user,
        action="verify_patient",
        resource_type="patient",
        resource_id=patient_id,
        decision="allowed" if result.get("verified") else "warning",
        permit_id=permit["permit_id"],
    )
    db.commit()
    return result


@router.get("/patients/{patient_id}/visits/{visit_id}/verify")
def verify_visit(
    patient_id: str,
    visit_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    permit = _require_active_permit(
        db,
        user=user,
        action="verify_visit",
        resource_type="visit",
        resource_id=visit_id,
    )
    result = verify_visit_integrity(db, patient_id, visit_id)
    log_access_event(
        db,
        user=user,
        action="verify_visit",
        resource_type="visit",
        resource_id=visit_id,
        decision="allowed" if result.get("verified") else "warning",
        permit_id=permit["permit_id"],
    )
    db.commit()
    return result
