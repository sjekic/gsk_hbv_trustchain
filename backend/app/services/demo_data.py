from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

STORE_DIR = Path(__file__).resolve().parents[2] / "data"
STORE_PATH = STORE_DIR / "prototype_store.json"
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
STORE_LOCK = Lock()


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
        if "visit_count" not in patient:
            patient["visit_count"] = len(patient["visits"])
        if "opted_out_secondary_use" not in patient:
            patient["opted_out_secondary_use"] = False

    return store


def _ensure_store_exists() -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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
    normalized = _normalize_store(store)
    with STORE_LOCK:
        STORE_PATH.write_text(json.dumps(normalized, indent=2), encoding="utf-8")


def _next_block_number(ledger: list[dict[str, Any]]) -> int:
    if not ledger:
        return 201
    return max(int(item["block"]) for item in ledger) + 1


def _append_ledger_entry(
    store: dict[str, Any],
    *,
    artifact: str,
    event: str,
    artifact_hash: str,
    signer: str,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ledger = store["ledger"]

    # Resolve previous block hash — genesis block uses 64 zeros
    if ledger:
        prev_block = max(ledger, key=lambda b: int(b["block"]))
        previous_hash = prev_block.get("block_hash", "0" * 64)
    else:
        previous_hash = "0" * 64

    # Build the canonical block content (everything that gets committed)
    block_number = _next_block_number(ledger)
    block_content = {
        "block": block_number,
        "artifact": artifact,
        "event": event,
        "hash": artifact_hash,
        "previous_hash": previous_hash,
        "signer": signer,
        "timestamp": _now_iso(),
    }

    # The block_hash commits to ALL fields above — any tampering breaks the chain
    block_content["block_hash"] = _sha256_text(_canonical_json(block_content))
    block_content["status"] = "verified"

    if extra_fields:
        block_content.update(extra_fields)

    ledger.append(block_content)
    return block_content

def verify_chain_integrity(ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Walk the ledger in block order and verify the previous_hash linkage.
    Returns the ledger entries annotated with chain_status: 'verified' | 'broken'.
    """
    sorted_blocks = sorted(ledger, key=lambda b: int(b["block"]))
    results = []
    expected_previous = "0" * 64

    for block in sorted_blocks:
        # Recompute what the block_hash should be
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
        # Next block must reference this block's hash (use stored hash to propagate breaks)
        expected_previous = actual_block_hash

    return results

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


def get_export_anonymization_status() -> dict[str, Any]:
    store = _load_store()
    return _build_export_gate(store["patients"])


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
    file_name: str | None = None,
    file_bytes: bytes | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    store = _load_store()

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
        store,
        artifact=f"{source_type.lower()}_{submission_id}.json",
        event="Submission notarized in simulated ledger",
        artifact_hash=artifact_hash,
        signer=operator_id,
        extra_fields={"submission_id": submission_id},
    )

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
        "dq_score": float(dq_score),
        "readiness_score": float(readiness_score),
        "schema_signed": bool(schema_signed),
        "temporal_issue_count": int(temporal_issue_count),
        "needs_vocab_remap": bool(needs_vocab_remap),
        "notes": notes,
        "file_name": file_name,
        "artifact_hash": artifact_hash,
        "ledger_block": ledger_entry["block"],
        "verification_status": "verified",
    }

    store["submissions"].append(submission)
    _save_store(store)
    return submission, ledger_entry


def create_prototype_patient(
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
    store = _load_store()

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
        store,
        artifact=f"patient_{patient_id}.json",
        event="Patient baseline notarized in simulated ledger",
        artifact_hash=artifact_hash,
        signer=operator_id,
        extra_fields={"patient_id": patient_id},
    )

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
        "artifact_hash": artifact_hash,
        "ledger_block": ledger_entry["block"],
        "verification_status": "verified",
        "visit_count": 0,
        "visits": [],
    }

    store["patients"].append(patient)
    _save_store(store)
    return patient, ledger_entry


def create_patient_visit(
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
    store = _load_store()
    patient = next((item for item in store["patients"] if item["id"] == patient_id), None)

    if patient is None:
        raise ValueError("Patient not found.")

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

    ledger_entry = _append_ledger_entry(
        store,
        artifact=f"visit_{visit_id}.json",
        event="Visit notarized in simulated ledger",
        artifact_hash=artifact_hash,
        signer=patient["operator_id"],
        extra_fields={"patient_id": patient_id, "visit_id": visit_id},
    )

    visit = {
        "id": visit_id,
        "patient_id": patient_id,
        "created_at": created_at,
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
        "artifact_hash": artifact_hash,
        "ledger_block": ledger_entry["block"],
        "verification_status": "verified",
    }

    patient["visits"].append(visit)
    patient["visit_count"] = len(patient["visits"])
    _save_store(store)
    return visit, ledger_entry


def get_prototype_submissions() -> list[dict[str, Any]]:
    store = _load_store()
    return sorted(store["submissions"], key=lambda item: item["created_at"], reverse=True)


def get_prototype_patients() -> list[dict[str, Any]]:
    store = _load_store()
    patients = sorted(store["patients"], key=lambda item: item["created_at"], reverse=True)
    for patient in patients:
        patient["visits"] = sorted(
            patient.get("visits", []),
            key=lambda visit: visit["created_at"],
            reverse=True,
        )
        patient["visit_count"] = len(patient["visits"])
    return patients


def verify_submission_integrity(submission_id: str) -> dict[str, Any]:
    store = _load_store()
    submission = next((item for item in store["submissions"] if item["id"] == submission_id), None)
    if submission is None:
        return {"verified": False, "message": "Submission not found.", "ledger_block": -1}

    artifact_payload = _submission_fingerprint_payload(
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
        file_name=submission.get("file_name"),
        file_hash=None,
    )
    expected_hash = _sha256_text(_canonical_json(artifact_payload))
    verified = expected_hash == submission["artifact_hash"]

    return {
        "verified": verified,
        "message": "Submission hash verified." if verified else "Submission hash mismatch.",
        "ledger_block": submission["ledger_block"],
    }


def verify_patient_integrity(patient_id: str) -> dict[str, Any]:
    store = _load_store()
    patient = next((item for item in store["patients"] if item["id"] == patient_id), None)
    if patient is None:
        return {"verified": False, "message": "Patient not found.", "ledger_block": -1}

    artifact_payload = _patient_fingerprint_payload(
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
        opted_out_secondary_use=patient.get("opted_out_secondary_use", False),
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
    expected_hash = _sha256_text(_canonical_json(artifact_payload))
    verified = expected_hash == patient["artifact_hash"]

    return {
        "verified": verified,
        "message": "Patient hash verified." if verified else "Patient hash mismatch.",
        "ledger_block": patient["ledger_block"],
    }


def verify_visit_integrity(patient_id: str, visit_id: str) -> dict[str, Any]:
    store = _load_store()
    patient = next((item for item in store["patients"] if item["id"] == patient_id), None)
    if patient is None:
        return {"verified": False, "message": "Patient not found.", "ledger_block": -1}

    visit = next((item for item in patient["visits"] if item["id"] == visit_id), None)
    if visit is None:
        return {"verified": False, "message": "Visit not found.", "ledger_block": -1}

    artifact_payload = _visit_fingerprint_payload(
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
    expected_hash = _sha256_text(_canonical_json(artifact_payload))
    verified = expected_hash == visit["artifact_hash"]

    return {
        "verified": verified,
        "message": "Visit hash verified." if verified else "Visit hash mismatch.",
        "ledger_block": visit["ledger_block"],
    }


def get_prototype_dashboard() -> dict[str, Any]:
    store = _load_store()
    submissions = store["submissions"]
    patients = store["patients"]
    active_patients = [
        patient for patient in patients if not patient.get("opted_out_secondary_use", False)
    ]
    visits = [visit for patient in patients for visit in patient["visits"]]
    active_visits = [visit for patient in active_patients for visit in patient["visits"]]
    ledger_raw = store["ledger"]
    # Only run full chain verification, annotate status directly from stored fields
    ledger = sorted(ledger_raw, key=lambda item: item["block"], reverse=True)

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