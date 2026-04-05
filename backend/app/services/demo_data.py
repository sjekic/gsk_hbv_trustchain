from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

STORE_DIR = Path(__file__).resolve().parents[2] / "data"
UPLOAD_DIR = STORE_DIR / "uploads"
STORE_PATH = STORE_DIR / "prototype_store.json"
STORE_LOCK = Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    base = Path(filename).name
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
    return safe or "upload.bin"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_json(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(encoded)


def _safe_float(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


def _date_lt(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    try:
        return date.fromisoformat(left) < date.fromisoformat(right)
    except ValueError:
        return False


def _ensure_store_exists() -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        seed = _build_seed_store()
        STORE_PATH.write_text(json.dumps(seed, indent=2), encoding="utf-8")


def _normalize_store(store: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    changed = False

    if "submissions" not in store:
        store["submissions"] = []
        changed = True
    if "ledger" not in store:
        store["ledger"] = []
        changed = True
    if "patients" not in store:
        store["patients"] = []
        changed = True

    for patient in store["patients"]:
        if "visits" not in patient:
            patient["visits"] = []
            changed = True

    return store, changed


def _load_store() -> dict[str, Any]:
    _ensure_store_exists()
    with STORE_LOCK:
        store = json.loads(STORE_PATH.read_text(encoding="utf-8"))
        store, changed = _normalize_store(store)
        if changed:
            STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")
        return store


def _save_store(store: dict[str, Any]) -> None:
    _ensure_store_exists()
    with STORE_LOCK:
        STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _artifact_payload(
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
        "dq_score": round(float(dq_score), 1),
        "readiness_score": round(float(readiness_score), 1),
        "schema_signed": bool(schema_signed),
        "temporal_issue_count": int(temporal_issue_count),
        "needs_vocab_remap": bool(needs_vocab_remap),
        "notes": notes.strip(),
        "file_hash": file_hash,
    }


def _patient_payload(
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
        "baseline_hbsag": _safe_float(baseline_hbsag),
        "baseline_hbv_dna": _safe_float(baseline_hbv_dna),
        "baseline_alt": _safe_float(baseline_alt),
        "baseline_ast": _safe_float(baseline_ast),
        "hbeag_status": hbeag_status,
        "bilirubin": _safe_float(bilirubin),
        "albumin": _safe_float(albumin),
        "inr": _safe_float(inr),
        "notes": notes.strip(),
    }


def _visit_payload(
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
        "quantitative_hbsag": _safe_float(quantitative_hbsag),
        "hbv_dna": _safe_float(hbv_dna),
        "hbv_dna_detectable": bool(hbv_dna_detectable),
        "alt": _safe_float(alt),
        "ast": _safe_float(ast),
        "hbeag_status": hbeag_status,
        "bilirubin": _safe_float(bilirubin),
        "albumin": _safe_float(albumin),
        "inr": _safe_float(inr),
        "on_na_therapy": bool(on_na_therapy),
        "on_bepirovirsen": bool(on_bepirovirsen),
        "functional_cure_endpoint": bool(functional_cure_endpoint),
        "notes": notes.strip(),
    }


def _public_submission(submission: dict[str, Any]) -> dict[str, Any]:
    hidden = {"upload_path", "file_hash"}
    return {k: v for k, v in submission.items() if k not in hidden}


def _public_visit(visit: dict[str, Any]) -> dict[str, Any]:
    return dict(visit)


def _public_patient(patient: dict[str, Any]) -> dict[str, Any]:
    public_patient = {k: v for k, v in patient.items() if k != "visits"}
    public_patient["visits"] = [_public_visit(item) for item in patient["visits"]]
    public_patient["visit_count"] = len(patient["visits"])
    return public_patient


def _build_seed_store() -> dict[str, Any]:
    seeds = [
        {
            "site_name": "Site Alpha",
            "source_type": "EHR",
            "country": "DE",
            "operator_id": "seed-loader",
            "record_count": 420,
            "hbv_cohort": 420,
            "bepirovirsen_treated": 0,
            "dq_score": 96.3,
            "readiness_score": 90.0,
            "schema_signed": True,
            "temporal_issue_count": 0,
            "needs_vocab_remap": False,
            "notes": "Structured EHR extract for longitudinal CHB journey.",
            "created_at": "2026-04-01T08:40:00Z",
        },
        {
            "site_name": "Site Beta",
            "source_type": "Laboratory",
            "country": "ES",
            "operator_id": "seed-loader",
            "record_count": 320,
            "hbv_cohort": 280,
            "bepirovirsen_treated": 0,
            "dq_score": 94.1,
            "readiness_score": 87.0,
            "schema_signed": True,
            "temporal_issue_count": 2,
            "needs_vocab_remap": False,
            "notes": "HBsAg, HBV DNA, ALT and AST observations across multiple visits.",
            "created_at": "2026-04-01T08:43:00Z",
        },
        {
            "site_name": "Site Gamma",
            "source_type": "Pharmacy",
            "country": "FR",
            "operator_id": "seed-loader",
            "record_count": 210,
            "hbv_cohort": 120,
            "bepirovirsen_treated": 112,
            "dq_score": 92.4,
            "readiness_score": 86.0,
            "schema_signed": False,
            "temporal_issue_count": 1,
            "needs_vocab_remap": False,
            "notes": "Dispensation feed with NA and bepirovirsen exposure history.",
            "created_at": "2026-04-01T09:00:00Z",
        },
        {
            "site_name": "Site Delta",
            "source_type": "Claims",
            "country": "IT",
            "operator_id": "seed-loader",
            "record_count": 180,
            "hbv_cohort": 98,
            "bepirovirsen_treated": 0,
            "dq_score": 90.2,
            "readiness_score": 84.0,
            "schema_signed": True,
            "temporal_issue_count": 0,
            "needs_vocab_remap": False,
            "notes": "Claims-like utilization feed for visits and procedures.",
            "created_at": "2026-04-01T09:12:00Z",
        },
        {
            "site_name": "Site Epsilon",
            "source_type": "Imaging",
            "country": "NL",
            "operator_id": "seed-loader",
            "record_count": 118,
            "hbv_cohort": 65,
            "bepirovirsen_treated": 0,
            "dq_score": 88.0,
            "readiness_score": 81.0,
            "schema_signed": True,
            "temporal_issue_count": 0,
            "needs_vocab_remap": True,
            "notes": "Imaging feed still requires additional OMOP vocabulary normalization.",
            "created_at": "2026-04-01T09:20:00Z",
        },
    ]

    submissions: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    base_block = 201

    for index, seed in enumerate(seeds, start=1):
        payload = _artifact_payload(
            site_name=seed["site_name"],
            source_type=seed["source_type"],
            country=seed["country"],
            operator_id=seed["operator_id"],
            record_count=seed["record_count"],
            hbv_cohort=seed["hbv_cohort"],
            bepirovirsen_treated=seed["bepirovirsen_treated"],
            dq_score=seed["dq_score"],
            readiness_score=seed["readiness_score"],
            schema_signed=seed["schema_signed"],
            temporal_issue_count=seed["temporal_issue_count"],
            needs_vocab_remap=seed["needs_vocab_remap"],
            notes=seed["notes"],
            file_hash=None,
        )
        artifact_hash = _sha256_json(payload)
        block = base_block + index - 1

        submission = {
            "id": f"seed-{index:03d}",
            "created_at": seed["created_at"],
            "site_name": seed["site_name"],
            "source_type": seed["source_type"],
            "country": seed["country"],
            "operator_id": seed["operator_id"],
            "record_count": seed["record_count"],
            "hbv_cohort": seed["hbv_cohort"],
            "bepirovirsen_treated": seed["bepirovirsen_treated"],
            "dq_score": seed["dq_score"],
            "readiness_score": seed["readiness_score"],
            "schema_signed": seed["schema_signed"],
            "temporal_issue_count": seed["temporal_issue_count"],
            "needs_vocab_remap": seed["needs_vocab_remap"],
            "notes": seed["notes"],
            "file_name": None,
            "upload_path": None,
            "file_hash": None,
            "artifact_hash": artifact_hash,
            "ledger_block": block,
            "verification_status": "verified",
        }
        submissions.append(submission)

        ledger.append(
            {
                "block": block,
                "artifact": f"{seed['source_type'].lower()}_{submission['id']}.json",
                "event": "Seed submission notarized in simulated ledger",
                "hash": artifact_hash,
                "signer": seed["operator_id"],
                "timestamp": seed["created_at"],
                "status": "verified",
                "submission_id": submission["id"],
            }
        )

    return {"submissions": submissions, "ledger": ledger, "patients": []}



def get_prototype_submissions() -> list[dict[str, Any]]:
    store = _load_store()
    submissions = sorted(store["submissions"], key=lambda item: item["created_at"], reverse=True)
    return [_public_submission(item) for item in submissions]


def get_prototype_patients() -> list[dict[str, Any]]:
    store = _load_store()
    patients = sorted(store["patients"], key=lambda item: item["created_at"], reverse=True)
    return [_public_patient(item) for item in patients]

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
                patient["baseline_hbsag"],
                patient["baseline_hbv_dna"],
                patient["baseline_alt"],
                patient["baseline_ast"],
                patient["bilirubin"],
                patient["albumin"],
                patient["inr"],
            ]
        )

    for visit in visits:
        measurement_rows += sum(
            value is not None
            for value in [
                visit["quantitative_hbsag"],
                visit["hbv_dna"],
                visit["alt"],
                visit["ast"],
                visit["bilirubin"],
                visit["albumin"],
                visit["inr"],
            ]
        )

    drug_rows = (
        sum(1 for patient in patients if patient["on_na_therapy"])
        + sum(1 for patient in patients if patient["started_bepirovirsen"])
        + sum(1 for visit in visits if visit["on_na_therapy"])
        + sum(1 for visit in visits if visit["on_bepirovirsen"])
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
        mapping_gaps.append(
            "No major OMOP mapping gaps are currently flagged in the prototype."
        )

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

def create_prototype_submission(
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
    file_bytes: bytes | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    store = _load_store()

    submission_id = uuid.uuid4().hex[:12]
    created_at = _now_iso()
    safe_name = _safe_filename(file_name)
    upload_path = None
    file_hash = None

    if file_bytes:
        file_hash = _sha256_bytes(file_bytes)
        upload_path = str(UPLOAD_DIR / f"{submission_id}_{safe_name}")
        Path(upload_path).write_bytes(file_bytes)

    payload = _artifact_payload(
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
        file_hash=file_hash,
    )
    artifact_hash = _sha256_json(payload)
    next_block = max((entry["block"] for entry in store["ledger"]), default=200) + 1

    submission = {
        "id": submission_id,
        "created_at": created_at,
        "site_name": site_name,
        "source_type": source_type,
        "country": country,
        "operator_id": operator_id,
        "record_count": int(record_count),
        "hbv_cohort": int(hbv_cohort),
        "bepirovirsen_treated": int(bepirovirsen_treated),
        "dq_score": round(float(dq_score), 1),
        "readiness_score": round(float(readiness_score), 1),
        "schema_signed": bool(schema_signed),
        "temporal_issue_count": int(temporal_issue_count),
        "needs_vocab_remap": bool(needs_vocab_remap),
        "notes": notes.strip(),
        "file_name": safe_name,
        "upload_path": upload_path,
        "file_hash": file_hash,
        "artifact_hash": artifact_hash,
        "ledger_block": next_block,
        "verification_status": "verified",
    }

    ledger_entry = {
        "block": next_block,
        "artifact": safe_name or f"{source_type.lower()}_{submission_id}.json",
        "event": "Site submission notarized in simulated ledger",
        "hash": artifact_hash,
        "signer": operator_id,
        "timestamp": created_at,
        "status": "verified",
        "submission_id": submission_id,
    }

    store["submissions"].append(submission)
    store["ledger"].append(ledger_entry)
    _save_store(store)

    return _public_submission(submission), ledger_entry


def create_prototype_patient(
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
    baseline_hbsag: float | None,
    baseline_hbv_dna: float | None,
    baseline_alt: float | None,
    baseline_ast: float | None,
    hbeag_status: str,
    bilirubin: float | None,
    albumin: float | None,
    inr: float | None,
    notes: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    store = _load_store()

    patient_id = uuid.uuid4().hex[:12]
    created_at = _now_iso()
    payload = _patient_payload(
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
    artifact_hash = _sha256_json(payload)
    next_block = max((entry["block"] for entry in store["ledger"]), default=200) + 1

    patient = {
        "id": patient_id,
        "created_at": created_at,
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
        "baseline_hbsag": _safe_float(baseline_hbsag),
        "baseline_hbv_dna": _safe_float(baseline_hbv_dna),
        "baseline_alt": _safe_float(baseline_alt),
        "baseline_ast": _safe_float(baseline_ast),
        "hbeag_status": hbeag_status,
        "bilirubin": _safe_float(bilirubin),
        "albumin": _safe_float(albumin),
        "inr": _safe_float(inr),
        "notes": notes.strip(),
        "artifact_hash": artifact_hash,
        "ledger_block": next_block,
        "verification_status": "verified",
        "visits": [],
    }

    ledger_entry = {
        "block": next_block,
        "artifact": f"patient_{patient_pseudonym}_{patient_id}.json",
        "event": "Patient baseline record notarized in simulated ledger",
        "hash": artifact_hash,
        "signer": operator_id,
        "timestamp": created_at,
        "status": "verified",
        "patient_id": patient_id,
    }

    store["patients"].append(patient)
    store["ledger"].append(ledger_entry)
    _save_store(store)

    return _public_patient(patient), ledger_entry


def create_patient_visit(
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
) -> tuple[dict[str, Any], dict[str, Any]]:
    store = _load_store()
    patient = next((item for item in store["patients"] if item["id"] == patient_id), None)

    if patient is None:
        raise ValueError("Patient not found.")

    visit_id = uuid.uuid4().hex[:12]
    created_at = _now_iso()
    payload = _visit_payload(
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
    artifact_hash = _sha256_json(payload)
    next_block = max((entry["block"] for entry in store["ledger"]), default=200) + 1

    visit = {
        "id": visit_id,
        "patient_id": patient_id,
        "created_at": created_at,
        "visit_date": visit_date,
        "visit_type": visit_type,
        "quantitative_hbsag": _safe_float(quantitative_hbsag),
        "hbv_dna": _safe_float(hbv_dna),
        "hbv_dna_detectable": bool(hbv_dna_detectable),
        "alt": _safe_float(alt),
        "ast": _safe_float(ast),
        "hbeag_status": hbeag_status,
        "bilirubin": _safe_float(bilirubin),
        "albumin": _safe_float(albumin),
        "inr": _safe_float(inr),
        "on_na_therapy": bool(on_na_therapy),
        "on_bepirovirsen": bool(on_bepirovirsen),
        "functional_cure_endpoint": bool(functional_cure_endpoint),
        "notes": notes.strip(),
        "artifact_hash": artifact_hash,
        "ledger_block": next_block,
        "verification_status": "verified",
    }

    ledger_entry = {
        "block": next_block,
        "artifact": f"visit_{patient['patient_pseudonym']}_{visit_id}.json",
        "event": "Patient visit record notarized in simulated ledger",
        "hash": artifact_hash,
        "signer": patient["operator_id"],
        "timestamp": created_at,
        "status": "verified",
        "patient_id": patient_id,
        "visit_id": visit_id,
    }

    patient["visits"].append(visit)
    store["ledger"].append(ledger_entry)
    _save_store(store)

    return _public_visit(visit), ledger_entry


def verify_submission_integrity(submission_id: str) -> dict[str, Any]:
    store = _load_store()
    submission = next((item for item in store["submissions"] if item["id"] == submission_id), None)

    if submission is None:
        return {"verified": False, "message": "Submission not found."}

    recomputed_file_hash = None
    if submission.get("upload_path"):
        upload_path = Path(submission["upload_path"])
        if upload_path.exists():
            recomputed_file_hash = _sha256_bytes(upload_path.read_bytes())

    payload = _artifact_payload(
        site_name=submission["site_name"],
        source_type=submission["source_type"],
        country=submission["country"],
        operator_id=submission["operator_id"],
        record_count=submission["record_count"],
        hbv_cohort=submission["hbv_cohort"],
        bepirovirsen_treated=submission["bepirovirsen_treated"],
        dq_score=submission["dq_score"],
        readiness_score=submission["readiness_score"],
        schema_signed=submission["schema_signed"],
        temporal_issue_count=submission["temporal_issue_count"],
        needs_vocab_remap=submission["needs_vocab_remap"],
        notes=submission["notes"],
        file_hash=recomputed_file_hash,
    )
    recomputed_hash = _sha256_json(payload)
    verified = recomputed_hash == submission["artifact_hash"]

    return {
        "verified": verified,
        "submission_id": submission_id,
        "stored_hash": submission["artifact_hash"],
        "recomputed_hash": recomputed_hash,
        "ledger_block": submission["ledger_block"],
        "message": "Integrity verified." if verified else "Integrity mismatch detected.",
    }


def verify_patient_integrity(patient_id: str) -> dict[str, Any]:
    store = _load_store()
    patient = next((item for item in store["patients"] if item["id"] == patient_id), None)

    if patient is None:
        return {"verified": False, "message": "Patient not found."}

    payload = _patient_payload(
        site_name=patient["site_name"],
        country=patient["country"],
        operator_id=patient["operator_id"],
        patient_pseudonym=patient["patient_pseudonym"],
        sex=patient["sex"],
        year_of_birth=patient["year_of_birth"],
        diagnosis_date=patient["diagnosis_date"],
        chronic_hbv_confirmed=patient["chronic_hbv_confirmed"],
        on_na_therapy=patient["on_na_therapy"],
        bepirovirsen_eligible=patient["bepirovirsen_eligible"],
        started_bepirovirsen=patient["started_bepirovirsen"],
        baseline_hbsag=patient["baseline_hbsag"],
        baseline_hbv_dna=patient["baseline_hbv_dna"],
        baseline_alt=patient["baseline_alt"],
        baseline_ast=patient["baseline_ast"],
        hbeag_status=patient["hbeag_status"],
        bilirubin=patient["bilirubin"],
        albumin=patient["albumin"],
        inr=patient["inr"],
        notes=patient["notes"],
    )
    recomputed_hash = _sha256_json(payload)
    verified = recomputed_hash == patient["artifact_hash"]

    return {
        "verified": verified,
        "patient_id": patient_id,
        "stored_hash": patient["artifact_hash"],
        "recomputed_hash": recomputed_hash,
        "ledger_block": patient["ledger_block"],
        "message": "Patient integrity verified." if verified else "Patient integrity mismatch detected.",
    }


def verify_visit_integrity(patient_id: str, visit_id: str) -> dict[str, Any]:
    store = _load_store()
    patient = next((item for item in store["patients"] if item["id"] == patient_id), None)

    if patient is None:
        return {"verified": False, "message": "Patient not found."}

    visit = next((item for item in patient["visits"] if item["id"] == visit_id), None)
    if visit is None:
        return {"verified": False, "message": "Visit not found."}

    payload = _visit_payload(
        patient_id=patient_id,
        visit_date=visit["visit_date"],
        visit_type=visit["visit_type"],
        quantitative_hbsag=visit["quantitative_hbsag"],
        hbv_dna=visit["hbv_dna"],
        hbv_dna_detectable=visit["hbv_dna_detectable"],
        alt=visit["alt"],
        ast=visit["ast"],
        hbeag_status=visit["hbeag_status"],
        bilirubin=visit["bilirubin"],
        albumin=visit["albumin"],
        inr=visit["inr"],
        on_na_therapy=visit["on_na_therapy"],
        on_bepirovirsen=visit["on_bepirovirsen"],
        functional_cure_endpoint=visit["functional_cure_endpoint"],
        notes=visit["notes"],
    )
    recomputed_hash = _sha256_json(payload)
    verified = recomputed_hash == visit["artifact_hash"]

    return {
        "verified": verified,
        "visit_id": visit_id,
        "stored_hash": visit["artifact_hash"],
        "recomputed_hash": recomputed_hash,
        "ledger_block": visit["ledger_block"],
        "message": "Visit integrity verified." if verified else "Visit integrity mismatch detected.",
    }


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)


def _patient_quality_score(patient: dict[str, Any]) -> float:
    score = 100.0
    if patient["baseline_hbsag"] is None:
        score -= 12
    if patient["baseline_hbv_dna"] is None:
        score -= 12
    if patient["baseline_alt"] is None:
        score -= 8
    if patient["baseline_ast"] is None:
        score -= 5
    if patient["hbeag_status"] in {"unknown", "", None}:
        score -= 5
    return round(max(55.0, score), 1)


def _visit_quality_score(patient: dict[str, Any], visit: dict[str, Any]) -> float:
    score = 100.0
    if visit["quantitative_hbsag"] is None:
        score -= 12
    if visit["hbv_dna"] is None:
        score -= 12
    if visit["alt"] is None:
        score -= 8
    if visit["ast"] is None:
        score -= 5
    if _date_lt(visit["visit_date"], patient["diagnosis_date"]):
        score -= 15
    return round(max(55.0, score), 1)


def _patient_readiness_score(patient: dict[str, Any]) -> float:
    score = 70.0
    if patient["chronic_hbv_confirmed"]:
        score += 10
    if patient["on_na_therapy"]:
        score += 5
    if patient["baseline_hbsag"] is not None:
        score += 5
    if patient["baseline_hbv_dna"] is not None:
        score += 5
    if patient["started_bepirovirsen"] or patient["bepirovirsen_eligible"]:
        score += 5
    if patient["visits"]:
        score += 5
    return round(min(100.0, score), 1)

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
                patient["baseline_hbsag"],
                patient["baseline_hbv_dna"],
                patient["baseline_alt"],
                patient["baseline_ast"],
                patient["bilirubin"],
                patient["albumin"],
                patient["inr"],
            ]
        )

    for visit in visits:
        measurement_rows += sum(
            value is not None
            for value in [
                visit["quantitative_hbsag"],
                visit["hbv_dna"],
                visit["alt"],
                visit["ast"],
                visit["bilirubin"],
                visit["albumin"],
                visit["inr"],
            ]
        )

    drug_rows = (
        sum(1 for patient in patients if patient["on_na_therapy"])
        + sum(1 for patient in patients if patient["started_bepirovirsen"])
        + sum(1 for visit in visits if visit["on_na_therapy"])
        + sum(1 for visit in visits if visit["on_bepirovirsen"])
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
        mapping_gaps.append(
            "No major OMOP mapping gaps are currently flagged in the prototype."
        )

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


def get_prototype_dashboard() -> dict[str, Any]:
    store = _load_store()
    submissions = store["submissions"]
    patients = store["patients"]
    visits = [visit for patient in patients for visit in patient["visits"]]
    ledger = sorted(store["ledger"], key=lambda item: item["block"], reverse=True)

    unique_sources = len({item["source_type"] for item in submissions})
    dataset_hbv_total = sum(item["hbv_cohort"] for item in submissions)
    treated_total = sum(item["bepirovirsen_treated"] for item in submissions) + sum(
        1 for patient in patients if patient["started_bepirovirsen"]
    )

    submission_dq_scores = [float(item["dq_score"]) for item in submissions]
    patient_dq_scores = [_patient_quality_score(item) for item in patients]
    visit_dq_scores = [
        _visit_quality_score(patient, visit)
        for patient in patients
        for visit in patient["visits"]
    ]
    avg_dq = _average(submission_dq_scores + patient_dq_scores + visit_dq_scores) or 90.0

    submission_readiness = [float(item["readiness_score"]) for item in submissions]
    patient_readiness = [_patient_readiness_score(item) for item in patients]
    avg_readiness = _average(submission_readiness + patient_readiness) or 85.0

    unsigned_sites = [item["site_name"] for item in submissions if not item["schema_signed"]]
    remap_sites = [item["site_name"] for item in submissions if item["needs_vocab_remap"]]
    temporal_total = sum(int(item["temporal_issue_count"]) for item in submissions)

    missing_baseline_hbsag = sum(1 for item in patients if item["baseline_hbsag"] is None)
    missing_baseline_hbv_dna = sum(1 for item in patients if item["baseline_hbv_dna"] is None)
    temporal_visit_issues = sum(
        1
        for patient in patients
        for visit in patient["visits"]
        if _date_lt(visit["visit_date"], patient["diagnosis_date"])
    )
    incomplete_visits = sum(
        1
        for patient in patients
        for visit in patient["visits"]
        if visit["quantitative_hbsag"] is None or visit["hbv_dna"] is None or visit["alt"] is None
    )

    schema_rate = round(
        100 * (sum(1 for item in submissions if item["schema_signed"]) / max(len(submissions), 1)),
        1,
    )
    total_artifacts = len(submissions) + len(patients) + len(visits)
    traceability = round(100 * (len(ledger) / max(total_artifacts, 1)), 1)
    traceability = min(traceability, 99.9)

    completeness_penalty = (missing_baseline_hbsag * 5) + (missing_baseline_hbv_dna * 5) + (incomplete_visits * 3)
    completeness = round(max(60.0, avg_dq - min(25.0, completeness_penalty)), 1)
    conformance = round((avg_dq * 0.5) + (schema_rate * 0.35) + (traceability * 0.15), 1)
    temporal_logic = round(max(60.0, 100.0 - ((temporal_total + temporal_visit_issues) * 4.0)), 1)
    interoperability = round(max(65.0, 100.0 - (len(remap_sites) * 8.0)), 1)

    critical_count = sum(
        1
        for item in submissions
        if float(item["dq_score"]) < 75 or int(item["temporal_issue_count"]) >= 5
    ) + sum(1 for patient in patients if _patient_quality_score(patient) < 70)

    high_count = sum(
        1
        for item in submissions
        if (not item["schema_signed"]) or item["needs_vocab_remap"]
    ) + missing_baseline_hbsag + missing_baseline_hbv_dna

    medium_count = temporal_total + temporal_visit_issues + incomplete_visits
    low_count = max((len(submissions) + len(patients) + len(visits)) - critical_count, 0)

    source_coverage_map: dict[str, int] = {}
    for item in submissions:
        source_coverage_map[item["source_type"]] = source_coverage_map.get(item["source_type"], 0) + int(item["record_count"])
    if patients:
        source_coverage_map["Patient registry"] = len(patients)
    if visits:
        source_coverage_map["Follow-up visits"] = len(visits)

    source_coverage = [
        {"source": source, "records": count}
        for source, count in sorted(source_coverage_map.items(), key=lambda entry: entry[1], reverse=True)
    ]

    source_feeds = _build_source_feeds(submissions)
    omop_etl = _build_omop_etl_summary(submissions, patients, visits, ledger)

    trend_events: list[dict[str, Any]] = []
    for item in submissions:
        trend_events.append(
            {
                "timestamp": item["created_at"],
                "label": item["site_name"][:8],
                "score": float(item["readiness_score"]),
            }
        )
    for item in patients:
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
            f"{missing_baseline_hbsag} patient baseline record(s) are missing HBsAg."
        )
    if missing_baseline_hbv_dna:
        open_findings.append(
            f"{missing_baseline_hbv_dna} patient baseline record(s) are missing HBV DNA."
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
    if not open_findings:
        open_findings.append("No open findings. Current dataset, patient, and visit records pass configured checks.")

    lifecycle_validation_status = "warning" if "No open findings" not in open_findings[0] else "complete"

    trial_readiness = [
        {
            "criterion": "Provenance chain available",
            "status": "Pass" if len(ledger) >= total_artifacts else "Monitor",
            "detail": f"{len(ledger)} ledger entries are available for {total_artifacts} stored artifacts.",
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
            "criterion": "Regulatory logging",
            "status": "Pass",
            "detail": "Each dataset, patient, and visit stores operator or signer, timestamp, artifact hash, and simulated block number.",
        },
        {
            "criterion": "HBV pathway observability",
            "status": "Pass" if patients else "Monitor",
            "detail": f"The prototype currently tracks {len(patients)} patient baseline record(s) and {len(visits)} visit record(s).",
        },
    ]

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
                "value": str(len(patients)),
                "note": "Structured baseline HBV patient records",
            },
            {
                "label": "Visits captured",
                "value": str(len(visits)),
                "note": "Structured longitudinal follow-up records",
            },
            {
                "label": "HBV cohort in datasets",
                "value": f"{dataset_hbv_total:,}",
                "note": "Reported cohort count across dataset submissions",
            },
            {
                "label": "Bepirovirsen-treated",
                "value": f"{treated_total:,}",
                "note": "Across current prototype artifacts",
            },
            {
                "label": "Data quality score",
                "value": f"{avg_dq:.1f}",
                "note": "Composite score across datasets, patients, and visits",
            },
            {
                "label": "Trials / RWE readiness",
                "value": f"{avg_readiness:.1f}%",
                "note": "Average readiness across current prototype artifacts",
            },
        ],
        "source_feeds": source_feeds,
        "omop_etl": omop_etl,
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
                "title": "Governance dashboard refresh",
                "description": "KPIs, charts, findings, patients, visits, and integrity verification refresh directly from the stored prototype data.",
                "checks": ["Live metrics", "Recent artifacts", "Integrity verification"],
                "status": "active",
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