from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import LedgerBlock, Patient, Submission, Visit

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"


# ── Pure helpers (unchanged) ──────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


def _date_lt(left: str, right: str) -> bool:
    try:
        return left < right
    except Exception:
        return False


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _omop_domain(artifact: str) -> str:
    if artifact.startswith("patient_"):
        return "CONDITION_OCCURRENCE + MEASUREMENT"
    elif artifact.startswith("visit_"):
        return "MEASUREMENT + OBSERVATION"
    elif artifact.startswith("consent_"):
        return "OBSERVATION"
    elif artifact.startswith("permit_"):
        return "NOTE"
    else:
        return "VISIT_OCCURRENCE"


# ── ORM → dict conversion ────────────────────────────────────────


def _dec(v: Any) -> Any:
    """Convert Decimal to float for JSON-safe output."""
    if isinstance(v, Decimal):
        return float(v)
    return v


def _submission_to_dict(s: Submission) -> dict[str, Any]:
    return {
        "id": s.id,
        "created_at": s.created_at,
        "site_name": s.site_name,
        "source_type": s.source_type,
        "country": s.country,
        "operator_id": s.operator_id,
        "record_count": s.record_count,
        "hbv_cohort": s.hbv_cohort,
        "bepirovirsen_treated": s.bepirovirsen_treated,
        "dq_score": _dec(s.dq_score),
        "readiness_score": _dec(s.readiness_score),
        "schema_signed": s.schema_signed,
        "temporal_issue_count": s.temporal_issue_count,
        "needs_vocab_remap": s.needs_vocab_remap,
        "notes": s.notes,
        "file_name": s.file_name,
        "artifact_hash": s.artifact_hash,
        "ledger_block": s.ledger_block,
        "verification_status": s.verification_status,
    }


def _visit_to_dict(v: Visit) -> dict[str, Any]:
    return {
        "id": v.id,
        "patient_id": v.patient_id,
        "created_at": v.created_at,
        "visit_date": v.visit_date,
        "visit_type": v.visit_type,
        "quantitative_hbsag": _dec(v.quantitative_hbsag),
        "hbv_dna": _dec(v.hbv_dna),
        "hbv_dna_detectable": v.hbv_dna_detectable,
        "alt": _dec(v.alt),
        "ast": _dec(v.ast),
        "hbeag_status": v.hbeag_status,
        "bilirubin": _dec(v.bilirubin),
        "albumin": _dec(v.albumin),
        "inr": _dec(v.inr),
        "on_na_therapy": v.on_na_therapy,
        "on_bepirovirsen": v.on_bepirovirsen,
        "functional_cure_endpoint": v.functional_cure_endpoint,
        "notes": v.notes,
        "artifact_hash": v.artifact_hash,
        "ledger_block": v.ledger_block,
        "verification_status": v.verification_status,
    }


def _patient_to_dict(p: Patient) -> dict[str, Any]:
    visits = sorted(p.visits, key=lambda v: v.created_at, reverse=True)
    return {
        "id": p.id,
        "created_at": p.created_at,
        "site_name": p.site_name,
        "country": p.country,
        "operator_id": p.operator_id,
        "patient_pseudonym": p.patient_pseudonym,
        "sex": p.sex,
        "year_of_birth": p.year_of_birth,
        "diagnosis_date": p.diagnosis_date,
        "chronic_hbv_confirmed": p.chronic_hbv_confirmed,
        "on_na_therapy": p.on_na_therapy,
        "bepirovirsen_eligible": p.bepirovirsen_eligible,
        "started_bepirovirsen": p.started_bepirovirsen,
        "opted_out_secondary_use": p.opted_out_secondary_use,
        "baseline_hbsag": _dec(p.baseline_hbsag),
        "baseline_hbv_dna": _dec(p.baseline_hbv_dna),
        "baseline_alt": _dec(p.baseline_alt),
        "baseline_ast": _dec(p.baseline_ast),
        "hbeag_status": p.hbeag_status,
        "bilirubin": _dec(p.bilirubin),
        "albumin": _dec(p.albumin),
        "inr": _dec(p.inr),
        "notes": p.notes,
        "artifact_hash": p.artifact_hash,
        "ledger_block": p.ledger_block,
        "verification_status": p.verification_status,
        "visit_count": p.visit_count,
        "visits": [_visit_to_dict(v) for v in visits],
    }


def _ledger_to_dict(b: LedgerBlock) -> dict[str, Any]:
    return {
        "block": b.block,
        "artifact": b.artifact,
        "event": b.event,
        "hash": b.hash,
        "previous_hash": b.previous_hash,
        "block_hash": b.block_hash,
        "signer": b.signer,
        "timestamp": b.timestamp,
        "status": b.status,
        "omop_domain": b.omop_domain,
        "submission_id": b.submission_id,
        "patient_id": b.patient_id,
        "visit_id": b.visit_id,
    }


# ── Fingerprint payloads (unchanged logic) ───────────────────────


def _submission_fingerprint_payload(
    *,
    site_name: str,
    source_type: str,
    country: str,
    operator_id: str,
    record_count: int,
    hbv_cohort: int,
    bepirovirsen_treated: int,
    dq_score: float,
    readiness_score: float,
    schema_signed: bool,
    temporal_issue_count: int,
    needs_vocab_remap: bool,
    notes: str,
    file_name: str | None,
    file_hash: str | None,
) -> dict[str, Any]:
    return {
        "site_name": site_name,
        "source_type": source_type,
        "country": country,
        "operator_id": operator_id,
        "record_count": int(record_count),
        "hbv_cohort": int(hbv_cohort),
        "bepirovirsen_treated": int(bepirovirsen_treated),
        "dq_score": float(dq_score),
        "readiness_score": float(readiness_score),
        "schema_signed": bool(schema_signed),
        "temporal_issue_count": int(temporal_issue_count),
        "needs_vocab_remap": bool(needs_vocab_remap),
        "notes": notes,
        "file_name": file_name,
        "file_hash": file_hash,
    }


def _patient_fingerprint_payload(
    *,
    site_name: str,
    country: str,
    operator_id: str,
    patient_pseudonym: str,
    sex: str,
    year_of_birth: int,
    diagnosis_date: str,
    chronic_hbv_confirmed: bool,
    on_na_therapy: bool,
    bepirovirsen_eligible: bool,
    started_bepirovirsen: bool,
    opted_out_secondary_use: bool,
    baseline_hbsag: float | None,
    baseline_hbv_dna: float | None,
    baseline_alt: float | None,
    baseline_ast: float | None,
    hbeag_status: str,
    bilirubin: float | None,
    albumin: float | None,
    inr: float | None,
    notes: str,
) -> dict[str, Any]:
    return {
        "site_name": site_name,
        "country": country,
        "operator_id": operator_id,
        "patient_pseudonym": patient_pseudonym,
        "sex": sex,
        "year_of_birth": int(year_of_birth),
        "diagnosis_date": diagnosis_date,
        "chronic_hbv_confirmed": bool(chronic_hbv_confirmed),
        "on_na_therapy": bool(on_na_therapy),
        "bepirovirsen_eligible": bool(bepirovirsen_eligible),
        "started_bepirovirsen": bool(started_bepirovirsen),
        "opted_out_secondary_use": bool(opted_out_secondary_use),
        "baseline_hbsag": baseline_hbsag,
        "baseline_hbv_dna": baseline_hbv_dna,
        "baseline_alt": baseline_alt,
        "baseline_ast": baseline_ast,
        "hbeag_status": hbeag_status,
        "bilirubin": bilirubin,
        "albumin": albumin,
        "inr": inr,
        "notes": notes,
    }


def _visit_fingerprint_payload(
    *,
    patient_id: str,
    visit_date: str,
    visit_type: str,
    quantitative_hbsag: float | None,
    hbv_dna: float | None,
    hbv_dna_detectable: bool,
    alt: float | None,
    ast: float | None,
    hbeag_status: str,
    bilirubin: float | None,
    albumin: float | None,
    inr: float | None,
    on_na_therapy: bool,
    on_bepirovirsen: bool,
    functional_cure_endpoint: bool,
    notes: str,
) -> dict[str, Any]:
    return {
        "patient_id": patient_id,
        "visit_date": visit_date,
        "visit_type": visit_type,
        "quantitative_hbsag": quantitative_hbsag,
        "hbv_dna": hbv_dna,
        "hbv_dna_detectable": bool(hbv_dna_detectable),
        "alt": alt,
        "ast": ast,
        "hbeag_status": hbeag_status,
        "bilirubin": bilirubin,
        "albumin": albumin,
        "inr": inr,
        "on_na_therapy": bool(on_na_therapy),
        "on_bepirovirsen": bool(on_bepirovirsen),
        "functional_cure_endpoint": bool(functional_cure_endpoint),
        "notes": notes,
    }


# ── Quality / readiness scoring (unchanged logic) ────────────────


def _patient_quality_score(patient: dict[str, Any]) -> float:
    key_fields = [
        patient.get("baseline_hbsag"),
        patient.get("baseline_hbv_dna"),
        patient.get("baseline_alt"),
        patient.get("baseline_ast"),
    ]
    completeness = sum(value is not None for value in key_fields) / len(key_fields)
    treatment_bonus = 5 if patient.get("started_bepirovirsen") or patient.get("on_na_therapy") else 0
    confirmation_bonus = 5 if patient.get("chronic_hbv_confirmed") else 0
    score = 70 + (completeness * 20) + treatment_bonus + confirmation_bonus
    return round(min(score, 99.0), 1)


def _visit_quality_score(patient: dict[str, Any], visit: dict[str, Any]) -> float:
    key_fields = [
        visit.get("quantitative_hbsag"),
        visit.get("hbv_dna"),
        visit.get("alt"),
        visit.get("ast"),
    ]
    completeness = sum(value is not None for value in key_fields) / len(key_fields)
    temporal_penalty = 10 if _date_lt(visit.get("visit_date", ""), patient.get("diagnosis_date", "")) else 0
    score = 72 + (completeness * 22) - temporal_penalty
    return round(max(min(score, 99.0), 50.0), 1)


def _patient_readiness_score(patient: dict[str, Any]) -> float:
    score = 75.0
    if patient.get("baseline_hbsag") is not None:
        score += 5
    if patient.get("baseline_hbv_dna") is not None:
        score += 5
    if patient.get("baseline_alt") is not None:
        score += 3
    if patient.get("started_bepirovirsen"):
        score += 4
    if patient.get("visit_count", 0) > 0:
        score += 4
    if patient.get("opted_out_secondary_use"):
        score -= 6
    return round(max(min(score, 98.0), 60.0), 1)


# ── Ledger helpers ────────────────────────────────────────────────


def _next_block_number(db: Session) -> int:
    max_block = db.query(func.max(LedgerBlock.block)).scalar()
    if max_block is None:
        return 201
    return max_block + 1


def _append_ledger_entry(
    db: Session,
    *,
    artifact: str,
    event: str,
    artifact_hash: str,
    signer: str,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prev_block = db.query(LedgerBlock).order_by(LedgerBlock.block.desc()).first()
    previous_hash = prev_block.block_hash if prev_block else "0" * 64

    block_number = _next_block_number(db)
    block_content = {
        "block": block_number,
        "artifact": artifact,
        "event": event,
        "hash": artifact_hash,
        "previous_hash": previous_hash,
        "signer": signer,
        "timestamp": _now_iso(),
    }
    block_content["block_hash"] = _sha256_text(_canonical_json(block_content))

    extra = extra_fields or {}
    row = LedgerBlock(
        block=block_number,
        artifact=artifact,
        event=event,
        hash=artifact_hash,
        previous_hash=previous_hash,
        block_hash=block_content["block_hash"],
        signer=signer,
        timestamp=block_content["timestamp"],
        status="verified",
        omop_domain=_omop_domain(artifact),
        submission_id=extra.get("submission_id"),
        patient_id=extra.get("patient_id"),
        visit_id=extra.get("visit_id"),
    )
    db.add(row)
    db.flush()

    return _ledger_to_dict(row)


def verify_chain_integrity(ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sorted_blocks = sorted(ledger, key=lambda b: int(b["block"]))
    results = []
    expected_previous = "0" * 64

    for block in sorted_blocks:
        canonical = {
            "block": block["block"],
            "artifact": block["artifact"],
            "event": block["event"],
            "hash": block["hash"],
            "previous_hash": block.get("previous_hash", "0" * 64),
            "signer": block["signer"],
            "timestamp": block["timestamp"],
        }
        expected_block_hash = _sha256_text(_canonical_json(canonical))
        actual_block_hash = block.get("block_hash", "")

        prev_hash_matches = block.get("previous_hash", "0" * 64) == expected_previous
        block_hash_matches = actual_block_hash == expected_block_hash

        chain_ok = prev_hash_matches and block_hash_matches
        annotated = dict(block)
        annotated["chain_status"] = "verified" if chain_ok else "broken"
        annotated["chain_broken_reason"] = (
            None if chain_ok else (
                "block_hash_mismatch" if not block_hash_matches else "previous_hash_mismatch"
            )
        )
        results.append(annotated)
        expected_previous = actual_block_hash

    return results


# ── CRUD functions ────────────────────────────────────────────────


def create_prototype_submission(
    db: Session,
    *,
    site_name: str,
    source_type: str,
    country: str,
    operator_id: str,
    record_count: int,
    hbv_cohort: int,
    bepirovirsen_treated: int,
    dq_score: float,
    readiness_score: float,
    schema_signed: bool,
    temporal_issue_count: int,
    needs_vocab_remap: bool,
    notes: str,
    file_name: str | None = None,
    file_bytes: bytes | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    file_hash = _sha256_bytes(file_bytes) if file_bytes else None
    if file_name and file_bytes:
        safe_name = f"{uuid.uuid4().hex[:12]}_{file_name}"
        (UPLOAD_DIR / safe_name).write_bytes(file_bytes)

    artifact_payload = _submission_fingerprint_payload(
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
        file_hash=file_hash,
    )
    artifact_hash = _sha256_text(_canonical_json(artifact_payload))

    submission_id = uuid.uuid4().hex[:12]
    created_at = _now_iso()

    ledger_entry = _append_ledger_entry(
        db,
        artifact=f"{source_type.lower()}_{submission_id}.json",
        event="Submission notarized in simulated ledger",
        artifact_hash=artifact_hash,
        signer=operator_id,
        extra_fields={"submission_id": submission_id},
    )

    row = Submission(
        id=submission_id,
        created_at=created_at,
        site_name=site_name,
        source_type=source_type,
        country=country,
        operator_id=operator_id,
        record_count=int(record_count),
        hbv_cohort=int(hbv_cohort),
        bepirovirsen_treated=int(bepirovirsen_treated),
        dq_score=float(dq_score),
        readiness_score=float(readiness_score),
        schema_signed=bool(schema_signed),
        temporal_issue_count=int(temporal_issue_count),
        needs_vocab_remap=bool(needs_vocab_remap),
        notes=notes,
        file_name=file_name,
        artifact_hash=artifact_hash,
        ledger_block=ledger_entry["block"],
        verification_status="verified",
    )
    db.add(row)
    db.flush()

    return _submission_to_dict(row), ledger_entry


def create_prototype_patient(
    db: Session,
    *,
    site_name: str,
    country: str,
    operator_id: str,
    patient_pseudonym: str,
    sex: str,
    year_of_birth: int,
    diagnosis_date: str,
    chronic_hbv_confirmed: bool = True,
    on_na_therapy: bool = False,
    bepirovirsen_eligible: bool = False,
    started_bepirovirsen: bool = False,
    opted_out_secondary_use: bool = False,
    baseline_hbsag: float | None = None,
    baseline_hbv_dna: float | None = None,
    baseline_alt: float | None = None,
    baseline_ast: float | None = None,
    hbeag_status: str = "unknown",
    bilirubin: float | None = None,
    albumin: float | None = None,
    inr: float | None = None,
    notes: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    artifact_payload = _patient_fingerprint_payload(
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
    artifact_hash = _sha256_text(_canonical_json(artifact_payload))

    patient_id = uuid.uuid4().hex[:12]
    created_at = _now_iso()

    ledger_entry = _append_ledger_entry(
        db,
        artifact=f"patient_{patient_id}.json",
        event="Patient baseline notarized in simulated ledger",
        artifact_hash=artifact_hash,
        signer=operator_id,
        extra_fields={"patient_id": patient_id},
    )

    row = Patient(
        id=patient_id,
        created_at=created_at,
        site_name=site_name,
        country=country,
        operator_id=operator_id,
        patient_pseudonym=patient_pseudonym,
        sex=sex,
        year_of_birth=int(year_of_birth),
        diagnosis_date=diagnosis_date,
        chronic_hbv_confirmed=bool(chronic_hbv_confirmed),
        on_na_therapy=bool(on_na_therapy),
        bepirovirsen_eligible=bool(bepirovirsen_eligible),
        started_bepirovirsen=bool(started_bepirovirsen),
        opted_out_secondary_use=bool(opted_out_secondary_use),
        baseline_hbsag=baseline_hbsag,
        baseline_hbv_dna=baseline_hbv_dna,
        baseline_alt=baseline_alt,
        baseline_ast=baseline_ast,
        hbeag_status=hbeag_status,
        bilirubin=bilirubin,
        albumin=albumin,
        inr=inr,
        notes=notes,
        artifact_hash=artifact_hash,
        ledger_block=ledger_entry["block"],
        verification_status="verified",
        visit_count=0,
    )
    db.add(row)
    db.flush()

    return _patient_to_dict(row), ledger_entry


def create_patient_visit(
    db: Session,
    *,
    patient_id: str,
    visit_date: str,
    visit_type: str,
    quantitative_hbsag: float | None = None,
    hbv_dna: float | None = None,
    hbv_dna_detectable: bool = True,
    alt: float | None = None,
    ast: float | None = None,
    hbeag_status: str = "unknown",
    bilirubin: float | None = None,
    albumin: float | None = None,
    inr: float | None = None,
    on_na_therapy: bool = False,
    on_bepirovirsen: bool = False,
    functional_cure_endpoint: bool = False,
    notes: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise ValueError("Patient not found.")

    patient_dict = _patient_to_dict(patient)

    artifact_payload = _visit_fingerprint_payload(
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
    artifact_hash = _sha256_text(_canonical_json(artifact_payload))

    visit_id = uuid.uuid4().hex[:12]
    created_at = _now_iso()

    # Compute quality/readiness for visit
    visit_dict_for_scoring = {
        "quantitative_hbsag": quantitative_hbsag,
        "hbv_dna": hbv_dna,
        "alt": alt,
        "ast": ast,
        "visit_date": visit_date,
    }
    dq_score = _visit_quality_score(patient_dict, visit_dict_for_scoring)
    readiness_score = _patient_readiness_score(patient_dict)

    ledger_entry = _append_ledger_entry(
        db,
        artifact=f"visit_{visit_id}.json",
        event="Visit notarized in simulated ledger",
        artifact_hash=artifact_hash,
        signer=patient.operator_id,
        extra_fields={"patient_id": patient_id, "visit_id": visit_id},
    )

    row = Visit(
        id=visit_id,
        patient_id=patient_id,
        created_at=created_at,
        visit_date=visit_date,
        visit_type=visit_type,
        quantitative_hbsag=quantitative_hbsag,
        hbv_dna=hbv_dna,
        hbv_dna_detectable=bool(hbv_dna_detectable),
        alt=alt,
        ast=ast,
        hbeag_status=hbeag_status,
        bilirubin=bilirubin,
        albumin=albumin,
        inr=inr,
        on_na_therapy=bool(on_na_therapy),
        on_bepirovirsen=bool(on_bepirovirsen),
        functional_cure_endpoint=bool(functional_cure_endpoint),
        notes=notes,
        artifact_hash=artifact_hash,
        ledger_block=ledger_entry["block"],
        verification_status="verified",
        dq_score=dq_score,
        readiness_score=readiness_score,
    )
    db.add(row)

    patient.visit_count = len(patient.visits) + 1
    db.flush()

    return _visit_to_dict(row), ledger_entry


# ── Read functions ────────────────────────────────────────────────


def get_prototype_submissions(db: Session) -> list[dict[str, Any]]:
    rows = db.query(Submission).order_by(Submission.created_at.desc()).all()
    return [_submission_to_dict(r) for r in rows]


def get_prototype_patients(db: Session) -> list[dict[str, Any]]:
    rows = db.query(Patient).order_by(Patient.created_at.desc()).all()
    results = []
    for p in rows:
        d = _patient_to_dict(p)
        d["visit_count"] = len(d["visits"])
        results.append(d)
    return results


def verify_submission_integrity(db: Session, submission_id: str) -> dict[str, Any]:
    s = db.query(Submission).filter(Submission.id == submission_id).first()
    if s is None:
        return {"verified": False, "message": "Submission not found.", "ledger_block": -1}

    sd = _submission_to_dict(s)
    artifact_payload = _submission_fingerprint_payload(
        site_name=sd["site_name"],
        source_type=sd["source_type"],
        country=sd["country"],
        operator_id=sd["operator_id"],
        record_count=sd["record_count"],
        hbv_cohort=sd["hbv_cohort"],
        bepirovirsen_treated=sd["bepirovirsen_treated"],
        dq_score=sd["dq_score"],
        readiness_score=sd["readiness_score"],
        schema_signed=sd["schema_signed"],
        temporal_issue_count=sd["temporal_issue_count"],
        needs_vocab_remap=sd["needs_vocab_remap"],
        notes=sd["notes"],
        file_name=sd.get("file_name"),
        file_hash=None,
    )
    expected_hash = _sha256_text(_canonical_json(artifact_payload))
    verified = expected_hash == sd["artifact_hash"]

    return {
        "verified": verified,
        "message": "Submission hash verified." if verified else "Submission hash mismatch.",
        "ledger_block": sd["ledger_block"],
    }


def verify_patient_integrity(db: Session, patient_id: str) -> dict[str, Any]:
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if p is None:
        return {"verified": False, "message": "Patient not found.", "ledger_block": -1}

    pd = _patient_to_dict(p)
    artifact_payload = _patient_fingerprint_payload(
        site_name=pd["site_name"],
        country=pd["country"],
        operator_id=pd["operator_id"],
        patient_pseudonym=pd["patient_pseudonym"],
        sex=pd["sex"],
        year_of_birth=pd["year_of_birth"],
        diagnosis_date=pd["diagnosis_date"],
        chronic_hbv_confirmed=pd["chronic_hbv_confirmed"],
        on_na_therapy=pd["on_na_therapy"],
        bepirovirsen_eligible=pd["bepirovirsen_eligible"],
        started_bepirovirsen=pd["started_bepirovirsen"],
        opted_out_secondary_use=pd.get("opted_out_secondary_use", False),
        baseline_hbsag=pd["baseline_hbsag"],
        baseline_hbv_dna=pd["baseline_hbv_dna"],
        baseline_alt=pd["baseline_alt"],
        baseline_ast=pd["baseline_ast"],
        hbeag_status=pd["hbeag_status"],
        bilirubin=pd["bilirubin"],
        albumin=pd["albumin"],
        inr=pd["inr"],
        notes=pd["notes"],
    )
    expected_hash = _sha256_text(_canonical_json(artifact_payload))
    verified = expected_hash == pd["artifact_hash"]

    return {
        "verified": verified,
        "message": "Patient hash verified." if verified else "Patient hash mismatch.",
        "ledger_block": pd["ledger_block"],
    }


def verify_visit_integrity(db: Session, patient_id: str, visit_id: str) -> dict[str, Any]:
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if p is None:
        return {"verified": False, "message": "Patient not found.", "ledger_block": -1}

    v = db.query(Visit).filter(Visit.id == visit_id, Visit.patient_id == patient_id).first()
    if v is None:
        return {"verified": False, "message": "Visit not found.", "ledger_block": -1}

    vd = _visit_to_dict(v)
    artifact_payload = _visit_fingerprint_payload(
        patient_id=patient_id,
        visit_date=vd["visit_date"],
        visit_type=vd["visit_type"],
        quantitative_hbsag=vd["quantitative_hbsag"],
        hbv_dna=vd["hbv_dna"],
        hbv_dna_detectable=vd["hbv_dna_detectable"],
        alt=vd["alt"],
        ast=vd["ast"],
        hbeag_status=vd["hbeag_status"],
        bilirubin=vd["bilirubin"],
        albumin=vd["albumin"],
        inr=vd["inr"],
        on_na_therapy=vd["on_na_therapy"],
        on_bepirovirsen=vd["on_bepirovirsen"],
        functional_cure_endpoint=vd["functional_cure_endpoint"],
        notes=vd["notes"],
    )
    expected_hash = _sha256_text(_canonical_json(artifact_payload))
    verified = expected_hash == vd["artifact_hash"]

    return {
        "verified": verified,
        "message": "Visit hash verified." if verified else "Visit hash mismatch.",
        "ledger_block": vd["ledger_block"],
    }


def get_export_anonymization_status(db: Session) -> dict[str, Any]:
    patients = get_prototype_patients(db)
    return _build_export_gate(patients)


def get_hbsag_trajectory(db: Session) -> dict[str, Any]:
    patients = get_prototype_patients(db)

    visit_order = [
        "baseline", "week4", "week8", "week12", "week24",
        "post_week4", "post_week8", "post_week12", "post_week24",
    ]
    bwell_ref = {
        "baseline": 2800, "week4": 1200, "week8": 600, "week12": 200,
        "week24": 48, "post_week4": 45, "post_week8": 42,
        "post_week12": 40, "post_week24": 38,
    }

    grouped: dict[str, list[float]] = {stage: [] for stage in visit_order}
    for patient in patients:
        for visit in patient.get("visits", []):
            vt = visit.get("visit_type", "")
            hbsag = visit.get("hbsag_iuml") or visit.get("quantitative_hbsag")
            if vt in grouped and hbsag is not None:
                grouped[vt].append(float(hbsag))

    trajectory = []
    for stage in visit_order:
        values = grouped[stage]
        mean_val = round(sum(values) / len(values), 2) if values else 0.0
        trajectory.append({
            "name": stage,
            "mean_hbsag": mean_val,
            "bwell_ref": bwell_ref[stage],
        })

    return {
        "trajectory": trajectory,
        "patient_count": len(patients),
    }


# ── Source feeds / OMOP ETL / export gate (unchanged logic) ──────


def _build_source_feeds(submissions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expected_sources = ["EHR", "Laboratory", "Imaging", "Pharmacy", "Claims", "Wearable"]
    feeds: list[dict[str, Any]] = []

    for source in expected_sources:
        source_items = [item for item in submissions if item["source_type"] == source]
        record_total = sum(int(item["record_count"]) for item in source_items)
        site_total = len({item["site_name"] for item in source_items})
        countries = sorted({item["country"] for item in source_items})
        country_scope = ", ".join(countries) if countries else "—"
        last_ingest = max((item["created_at"] for item in source_items), default="No feed yet")
        avg_dq = _average([float(item["dq_score"]) for item in source_items]) if source_items else 0.0
        signed_total = sum(1 for item in source_items if item["schema_signed"])
        needs_remap = any(bool(item["needs_vocab_remap"]) for item in source_items)

        if not source_items:
            schema_status = "No feed"
            integrity_status = "Pending"
            linkage_status = "Not linked"
            feed_status = "pending"
            note = "No submissions received for this source yet."
        else:
            if signed_total == len(source_items):
                schema_status = "Signed"
            elif signed_total == 0:
                schema_status = "Missing"
            else:
                schema_status = "Partial"

            integrity_status = "Verified" if schema_status == "Signed" else "Attention"

            if needs_remap:
                linkage_status = "Partial"
                feed_status = "warning"
                note = "Terminology remap is still needed before full longitudinal linkage."
            elif schema_status != "Signed":
                linkage_status = "Partial"
                feed_status = "warning"
                note = "Schema signatures or source controls need review."
            else:
                linkage_status = "Linked"
                feed_status = "healthy"
                note = "Feed is ingestion-ready and linked into the prototype research layer."

        feeds.append(
            {
                "source": source,
                "records": record_total,
                "sites": site_total,
                "countries": country_scope,
                "last_ingest": last_ingest,
                "avg_dq": avg_dq,
                "schema_status": schema_status,
                "integrity_status": integrity_status,
                "linkage_status": linkage_status,
                "feed_status": feed_status,
                "note": note,
            }
        )

    return feeds


def _build_omop_etl_summary(
    submissions: list[dict[str, Any]],
    patients: list[dict[str, Any]],
    visits: list[dict[str, Any]],
    ledger: list[dict[str, Any]],
) -> dict[str, Any]:
    total_submissions = len(submissions)
    signed_total = sum(1 for item in submissions if item["schema_signed"])
    remap_total = sum(1 for item in submissions if item["needs_vocab_remap"])

    measurement_rows = 0
    for patient in patients:
        measurement_rows += sum(
            value is not None
            for value in [
                patient.get("baseline_hbsag"),
                patient.get("baseline_hbv_dna"),
                patient.get("baseline_alt"),
                patient.get("baseline_ast"),
                patient.get("bilirubin"),
                patient.get("albumin"),
                patient.get("inr"),
            ]
        )

    for visit in visits:
        measurement_rows += sum(
            value is not None
            for value in [
                visit.get("quantitative_hbsag"),
                visit.get("hbv_dna"),
                visit.get("alt"),
                visit.get("ast"),
                visit.get("bilirubin"),
                visit.get("albumin"),
                visit.get("inr"),
            ]
        )

    drug_rows = (
        sum(1 for patient in patients if patient.get("on_na_therapy"))
        + sum(1 for patient in patients if patient.get("started_bepirovirsen"))
        + sum(1 for visit in visits if visit.get("on_na_therapy"))
        + sum(1 for visit in visits if visit.get("on_bepirovirsen"))
    )

    mapping_coverage = 0.0
    vocabulary_coverage = 0.0
    quality_gate_pass_rate = 0.0

    if total_submissions > 0:
        signed_ratio = 100 * (signed_total / total_submissions)
        quality_gate_pass_rate = _average([float(item["dq_score"]) for item in submissions])

        mapping_coverage = round(
            max(
                60.0,
                min(
                    98.0,
                    (signed_ratio * 0.55)
                    + ((100 - (remap_total * 12)) * 0.25)
                    + (10.0 if patients else 0.0)
                    + (8.0 if visits else 0.0),
                ),
            ),
            1,
        )

        vocabulary_coverage = round(
            max(
                65.0,
                min(
                    99.0,
                    96.0 - (remap_total * 10.0) - ((total_submissions - signed_total) * 3.0),
                ),
            ),
            1,
        )

    status = "warning" if remap_total > 0 or signed_total < total_submissions else "complete"
    latest_timestamp = ledger[0]["timestamp"] if ledger else "—"
    latest_block = ledger[0]["block"] if ledger else None

    mapping_gaps: list[str] = []
    if remap_total > 0:
        mapping_gaps.append(
            f"{remap_total} source feed(s) still require vocabulary normalization before full OMOP standardization."
        )
    if signed_total < total_submissions:
        mapping_gaps.append(
            f"{total_submissions - signed_total} submission(s) are not fully schema-signed, so ETL trust is reduced."
        )
    if not patients:
        mapping_gaps.append(
            "No structured patient registry records are present yet, so PERSON-level OMOP loads are minimal."
        )
    if not visits:
        mapping_gaps.append(
            "No longitudinal visit records are present yet, so VISIT_OCCURRENCE and MEASUREMENT growth is limited."
        )
    if not mapping_gaps:
        mapping_gaps.append("No major OMOP mapping gaps are currently flagged in the prototype.")

    return {
        "current_snapshot": {
            "snapshot_id": f"omop_snapshot_{len(ledger):03d}",
            "snapshot_status": status,
            "mapping_coverage": mapping_coverage,
            "vocabulary_coverage": vocabulary_coverage,
            "quality_gate_pass_rate": quality_gate_pass_rate,
            "snapshot_block": latest_block,
        },
        "run_context": {
            "run_id": f"etl_run_{len(ledger):03d}",
            "etl_spec_version": "hbv-omop-spec-v0.3",
            "vocabulary_release": "Prototype mapped vocabularies",
            "target_cdm": "OMOP CDM v5.4",
            "last_run_at": latest_timestamp,
            "status": status,
        },
        "domain_loads": [
            {
                "domain": "PERSON",
                "rows": len(patients),
                "note": "Pseudonymised HBV patient registry records",
            },
            {
                "domain": "OBSERVATION_PERIOD",
                "rows": len(patients),
                "note": "Derived longitudinal observation windows",
            },
            {
                "domain": "VISIT_OCCURRENCE",
                "rows": len(visits),
                "note": "Structured screening, baseline, on-treatment, follow-up, and post-treatment visits",
            },
            {
                "domain": "MEASUREMENT",
                "rows": measurement_rows,
                "note": "HBsAg, HBV DNA, ALT, AST, bilirubin, albumin, INR, and related markers",
            },
            {
                "domain": "DRUG_EXPOSURE",
                "rows": drug_rows,
                "note": "NA therapy and bepirovirsen treatment state records",
            },
            {
                "domain": "CONDITION_OCCURRENCE",
                "rows": len(patients),
                "note": "Baseline chronic hepatitis B condition capture",
            },
        ],
        "mapping_gaps": mapping_gaps,
    }


def _build_export_gate(patients: list[dict[str, Any]]) -> dict[str, Any]:
    k_threshold = 5
    eligible_patients = [
        patient for patient in patients if not patient.get("opted_out_secondary_use", False)
    ]
    opted_out_patients = len(patients) - len(eligible_patients)

    cell_counts: dict[str, int] = {}
    for patient in eligible_patients:
        treatment_group = (
            "bepirovirsen"
            if patient.get("started_bepirovirsen")
            else "na_therapy"
            if patient.get("on_na_therapy")
            else "untreated"
        )
        cell_key = f"{patient.get('country', '—')} | {treatment_group}"
        cell_counts[cell_key] = cell_counts.get(cell_key, 0) + 1

    failing_cells = [
        {"cell": cell, "count": count}
        for cell, count in sorted(cell_counts.items())
        if count < k_threshold
    ]
    smallest_cell = min(cell_counts.values()) if cell_counts else 0

    passed = len(eligible_patients) >= k_threshold and len(failing_cells) == 0

    if passed:
        message = (
            f"Export permitted. All result cells meet the prototype anonymization threshold "
            f"(k≥{k_threshold})."
        )
    elif len(eligible_patients) < k_threshold:
        message = (
            f"Export blocked. Only {len(eligible_patients)} eligible patient(s) remain after "
            f"opt-out filtering, below k≥{k_threshold}."
        )
    else:
        message = (
            f"Export blocked. {len(failing_cells)} result cell(s) fall below the prototype "
            f"anonymization threshold (k≥{k_threshold}) and must be suppressed."
        )

    return {
        "passed": passed,
        "message": message,
        "k_threshold": k_threshold,
        "eligible_patients": len(eligible_patients),
        "opted_out_patients": opted_out_patients,
        "smallest_cell": smallest_cell,
        "failing_cells": failing_cells,
    }


# ── Dashboard builder ─────────────────────────────────────────────


def get_prototype_dashboard(db: Session) -> dict[str, Any]:
    submissions = get_prototype_submissions(db)
    patients = get_prototype_patients(db)
    active_patients = [
        patient for patient in patients if not patient.get("opted_out_secondary_use", False)
    ]
    visits = [visit for patient in patients for visit in patient["visits"]]
    active_visits = [visit for patient in active_patients for visit in patient["visits"]]
    ledger_rows = db.query(LedgerBlock).order_by(LedgerBlock.block.desc()).all()
    ledger = [_ledger_to_dict(b) for b in ledger_rows]

    unique_sources = len({item["source_type"] for item in submissions})
    dataset_hbv_total = sum(item["hbv_cohort"] for item in submissions)
    opted_out_patients = len(patients) - len(active_patients)
    treated_total = sum(item["bepirovirsen_treated"] for item in submissions) + sum(
        1 for patient in active_patients if patient["started_bepirovirsen"]
    )

    submission_dq_scores = [float(item["dq_score"]) for item in submissions]
    patient_dq_scores = [_patient_quality_score(item) for item in active_patients]
    visit_dq_scores = [
        _visit_quality_score(patient, visit)
        for patient in active_patients
        for visit in patient["visits"]
    ]
    avg_dq = _average(submission_dq_scores + patient_dq_scores + visit_dq_scores) or 90.0

    submission_readiness = [float(item["readiness_score"]) for item in submissions]
    patient_readiness = [_patient_readiness_score(item) for item in active_patients]
    avg_readiness = _average(submission_readiness + patient_readiness) or 85.0

    unsigned_sites = [item["site_name"] for item in submissions if not item["schema_signed"]]
    remap_sites = [item["site_name"] for item in submissions if item["needs_vocab_remap"]]
    temporal_total = sum(int(item["temporal_issue_count"]) for item in submissions)

    missing_baseline_hbsag = sum(1 for item in active_patients if item["baseline_hbsag"] is None)
    missing_baseline_hbv_dna = sum(1 for item in active_patients if item["baseline_hbv_dna"] is None)
    temporal_visit_issues = sum(
        1
        for patient in active_patients
        for visit in patient["visits"]
        if _date_lt(visit["visit_date"], patient["diagnosis_date"])
    )
    incomplete_visits = sum(
        1
        for patient in active_patients
        for visit in patient["visits"]
        if visit["quantitative_hbsag"] is None
        or visit["hbv_dna"] is None
        or visit["alt"] is None
    )

    schema_rate = round(
        100 * (sum(1 for item in submissions if item["schema_signed"]) / max(len(submissions), 1)),
        1,
    )
    total_artifacts = len(submissions) + len(active_patients) + len(active_visits)
    traceability = round(100 * (len(ledger) / max(total_artifacts, 1)), 1)
    traceability = min(traceability, 99.9)

    completeness_penalty = (
        (missing_baseline_hbsag * 5)
        + (missing_baseline_hbv_dna * 5)
        + (incomplete_visits * 3)
    )
    completeness = round(max(60.0, avg_dq - min(25.0, completeness_penalty)), 1)
    conformance = round((avg_dq * 0.5) + (schema_rate * 0.35) + (traceability * 0.15), 1)
    temporal_logic = round(max(60.0, 100.0 - ((temporal_total + temporal_visit_issues) * 4.0)), 1)
    interoperability = round(max(65.0, 100.0 - (len(remap_sites) * 8.0)), 1)

    critical_count = sum(
        1
        for item in submissions
        if float(item["dq_score"]) < 75 or int(item["temporal_issue_count"]) >= 5
    ) + sum(1 for patient in active_patients if _patient_quality_score(patient) < 70)

    high_count = sum(
        1 for item in submissions if (not item["schema_signed"]) or item["needs_vocab_remap"]
    ) + missing_baseline_hbsag + missing_baseline_hbv_dna

    medium_count = temporal_total + temporal_visit_issues + incomplete_visits
    low_count = max((len(submissions) + len(active_patients) + len(active_visits)) - critical_count, 0)

    source_coverage_map: dict[str, int] = {}
    for item in submissions:
        source_coverage_map[item["source_type"]] = (
            source_coverage_map.get(item["source_type"], 0) + int(item["record_count"])
        )
    if active_patients:
        source_coverage_map["Patient registry"] = len(active_patients)
    if active_visits:
        source_coverage_map["Follow-up visits"] = len(active_visits)

    source_coverage = [
        {"source": source, "records": count}
        for source, count in sorted(source_coverage_map.items(), key=lambda entry: entry[1], reverse=True)
    ]

    source_feeds = _build_source_feeds(submissions)
    omop_etl = _build_omop_etl_summary(submissions, active_patients, active_visits, ledger)
    export_gate = _build_export_gate(patients)

    trend_events: list[dict[str, Any]] = []
    for item in submissions:
        trend_events.append(
            {
                "timestamp": item["created_at"],
                "label": item["site_name"][:8],
                "score": float(item["readiness_score"]),
            }
        )
    for item in active_patients:
        trend_events.append(
            {
                "timestamp": item["created_at"],
                "label": item["patient_pseudonym"][:8],
                "score": _patient_readiness_score(item),
            }
        )

    trend_events = sorted(trend_events, key=lambda event: event["timestamp"])[-6:]
    readiness_trend = [
        {"month": event["label"], "score": round(event["score"], 1)}
        for event in trend_events
    ]

    open_findings: list[str] = []
    if unsigned_sites:
        open_findings.append(
            f"{len(unsigned_sites)} dataset submission(s) are missing signed schema manifests: "
            + ", ".join(unsigned_sites[:3])
            + "."
        )
    if missing_baseline_hbsag:
        open_findings.append(
            f"{missing_baseline_hbsag} eligible patient baseline record(s) are missing HBsAg."
        )
    if missing_baseline_hbv_dna:
        open_findings.append(
            f"{missing_baseline_hbv_dna} eligible patient baseline record(s) are missing HBV DNA."
        )
    if temporal_total + temporal_visit_issues:
        open_findings.append(
            f"{temporal_total + temporal_visit_issues} temporal inconsistency flag(s) are currently open."
        )
    if remap_sites:
        open_findings.append(
            f"{len(remap_sites)} source(s) still require OMOP terminology remapping: "
            + ", ".join(remap_sites[:3])
            + "."
        )
    if opted_out_patients:
        open_findings.append(
            f"{opted_out_patients} patient record(s) are opted out and excluded from secondary-use analytics."
        )
    if not open_findings:
        open_findings.append(
            "No open findings. Current eligible dataset, patient, and visit records pass configured checks."
        )

    _bepirovirsen_patients = [p for p in patients if any(v.get("started_bepirovirsen") for v in p.get("visits", []))]
    _functional_cure_patients = [p for p in _bepirovirsen_patients if any(v.get("functional_cure_endpoint") for v in p.get("visits", []))]
    _bepi_count = len(_bepirovirsen_patients)
    _functional_cures = len(_functional_cure_patients)
    _cure_rate = (_functional_cures / _bepi_count * 100) if _bepi_count else 0.0

    has_quality_findings = bool(
        unsigned_sites
        or missing_baseline_hbsag
        or missing_baseline_hbv_dna
        or (temporal_total + temporal_visit_issues)
        or remap_sites
    )
    lifecycle_validation_status = "warning" if has_quality_findings else "complete"

    trial_readiness = [
        {
            "criterion": "Provenance chain available",
            "status": "Pass" if len(ledger) >= total_artifacts else "Monitor",
            "detail": f"{len(ledger)} ledger entries are available for {total_artifacts} eligible stored artifacts.",
        },
        {
            "criterion": "Cross-source interoperability",
            "status": "Monitor" if remap_sites else "Pass",
            "detail": (
                "One or more source feeds still require vocabulary normalization."
                if remap_sites
                else "Current source feeds are aligned to the harmonized prototype model."
            ),
        },
        {
            "criterion": "Dataset and patient validation coverage",
            "status": "Pass" if avg_dq >= 85 else "Monitor",
            "detail": f"Current composite data quality score is {avg_dq}.",
        },
        {
            "criterion": "Secondary-use opt-out enforcement",
            "status": "Pass",
            "detail": f"{opted_out_patients} opted-out patient(s) are excluded from analytics and export checks.",
        },
        {
            "criterion": "Export anonymization gate",
            "status": "Pass" if export_gate["passed"] else "Monitor",
            "detail": export_gate["message"],
        },
    ]

    return {
        "prototype": {
            "name": "RWD TrustChain",
            "subtitle": "Interactive prototype for secure dataset intake, patient/visit capture, validation, simulated ledger notarization, EHDS opt-out filtering, and anonymization-gated result export.",
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
        "top_cards": [
            {
                "label": "Integrated sources",
                "value": str(unique_sources),
                "note": "Distinct dataset source types represented in the prototype store",
            },
            {
                "label": "Submitted datasets",
                "value": str(len(submissions)),
                "note": "Dataset-level artifacts hashed and linked to simulated ledger blocks",
            },
            {
                "label": "Patients tracked",
                "value": str(len(active_patients)),
                "note": f"{opted_out_patients} opted out, excluded from RWE queries",
            },
            {
                "label": "Visits captured",
                "value": str(len(active_visits)),
                "note": "Structured longitudinal follow-up records for eligible patients",
            },
            {
                "label": "HBV cohort in datasets",
                "value": f"{dataset_hbv_total:,}",
                "note": "Reported cohort count across dataset submissions",
            },
            {
                "label": "Bepirovirsen-treated",
                "value": f"{treated_total:,}",
                "note": "Across current eligible prototype artifacts",
            },
            {
                "label": "Data quality score",
                "value": f"{avg_dq:.1f}",
                "note": "Composite score across datasets and eligible patient/visit records",
            },
            {
                "label": "Trials / RWE readiness",
                "value": f"{avg_readiness:.1f}%",
                "note": "Average readiness across current eligible prototype artifacts",
            },
            {
                "label": "Functional cure rate",
                "value": f"{_cure_rate:.1f}%",
                "note": f"{_functional_cures}/{_bepi_count} bepirovirsen patients \u00b7 B-Well primary endpoint",
            },
        ],
        "source_feeds": source_feeds,
        "omop_etl": omop_etl,
        "export_gate": export_gate,
        "data_lifecycle": [
            {
                "step": 1,
                "title": "Dataset or patient entry",
                "description": "A site submits dataset metadata or a clinician enters a pseudonymised HBV patient baseline record.",
                "checks": ["Operator captured", "Site tagged", "Country tagged"],
                "status": "complete",
            },
            {
                "step": 2,
                "title": "Secure local persistence",
                "description": "The backend stores dataset submissions, structured patient records, visits, and optional uploaded artifacts.",
                "checks": ["JSON store", "Upload folder", "Timestamp"],
                "status": "complete",
            },
            {
                "step": 3,
                "title": "Artifact fingerprinting",
                "description": "The backend computes a SHA-256 hash over each dataset, patient baseline, or visit payload.",
                "checks": ["SHA-256", "Canonical payload", "Immutable fingerprint"],
                "status": "complete",
            },
            {
                "step": 4,
                "title": "Validation and issue detection",
                "description": "Schema flags, temporal checks, and missing HBV variables influence the live DQ and readiness views.",
                "checks": ["Schema signed", "Temporal issues", "HBV variable completeness"],
                "status": lifecycle_validation_status,
            },
            {
                "step": 5,
                "title": "Simulated ledger append",
                "description": "A new append-only block record is created with block number, signer, timestamp, and artifact hash.",
                "checks": ["Block number", "Signer", "Artifact hash"],
                "status": "complete",
            },
            {
                "step": 6,
                "title": "Secondary-use analytics",
                "description": "Dashboard analytics run only on permit-authorized, opt-out-filtered patient and visit records.",
                "checks": ["Permit active", "Opt-outs excluded", "Eligible cohort only"],
                "status": "active",
            },
            {
                "step": 7,
                "title": "Anonymization gate",
                "description": "Before result export, the prototype checks a mock k-anonymity rule and suppresses cells below threshold.",
                "checks": ["k≥5", "Cell suppression", "Non-personal export only"],
                "status": "complete" if export_gate["passed"] else "warning",
            },
        ],
        "ledger": ledger,
        "quality": {
            "dimensions": [
                {"name": "Completeness", "score": completeness},
                {"name": "Conformance", "score": conformance},
                {"name": "Temporal logic", "score": temporal_logic},
                {"name": "Traceability", "score": traceability},
                {"name": "Interoperability", "score": interoperability},
            ],
            "issue_severity": [
                {"severity": "Critical", "count": critical_count},
                {"severity": "High", "count": high_count},
                {"severity": "Medium", "count": medium_count},
                {"severity": "Low", "count": low_count},
            ],
            "readiness_trend": readiness_trend,
            "source_coverage": source_coverage,
            "open_findings": open_findings,
        },
        "trial_readiness": trial_readiness,
        "next_steps": [
            "Replace the JSON prototype store with PostgreSQL tables and controlled user authentication.",
            "Map structured patient and visit data into OMOP staging and transformation pipelines.",
            "Swap the simulated ledger with the permissioned Hyperledger Fabric notary when true networked provenance is needed.",
            "Add role-specific review queues for clinician approval, data stewardship, and audit export.",
        ],
    }
