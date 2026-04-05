from sqlalchemy import String, Date, DateTime, Boolean, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base
import datetime as dt


class DatasetSnapshot(Base):
    __tablename__ = "dataset_snapshot"
    __table_args__ = {"schema": "trustchain"}

    snapshot_id: Mapped[str] = mapped_column(String, primary_key=True)
    snapshot_label: Mapped[str] = mapped_column(String, nullable=False)
    omop_release_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    cdm_version: Mapped[str] = mapped_column(String, nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String, nullable=False)
    storage_uri: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=dt.datetime.utcnow)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    etl_version: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)


class PipelineRun(Base):
    __tablename__ = "pipeline_run"
    __table_args__ = {"schema": "trustchain"}

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("trustchain.dataset_snapshot.snapshot_id"))
    source_system: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    run_status: Mapped[str] = mapped_column(String, nullable=False)
    schema_check_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    linkage_performed: Mapped[bool] = mapped_column(Boolean, default=False)
    dq_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    critical_issue_count: Mapped[int] = mapped_column(nullable=False, default=0)


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issue"
    __table_args__ = {"schema": "trustchain"}

    issue_id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("trustchain.pipeline_run.run_id"), nullable=False)
    issue_code: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    omop_table: Mapped[str | None] = mapped_column(String)
    omop_field: Mapped[str | None] = mapped_column(String)
    affected_count: Mapped[int | None] = mapped_column()
    issue_summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="open")


# ── Prototype models ──────────────────────────────────────────────


class Submission(Base):
    __tablename__ = "submission"
    __table_args__ = {"schema": "trustchain"}

    id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    site_name: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    country: Mapped[str] = mapped_column(String, nullable=False)
    operator_id: Mapped[str] = mapped_column(String, nullable=False)
    record_count: Mapped[int] = mapped_column(nullable=False)
    hbv_cohort: Mapped[int] = mapped_column(nullable=False)
    bepirovirsen_treated: Mapped[int] = mapped_column(nullable=False)
    dq_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    readiness_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    schema_signed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    temporal_issue_count: Mapped[int] = mapped_column(nullable=False)
    needs_vocab_remap: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    file_name: Mapped[str | None] = mapped_column(String, nullable=True)
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ledger_block: Mapped[int] = mapped_column(nullable=False)
    verification_status: Mapped[str] = mapped_column(String, default="verified")


class Patient(Base):
    __tablename__ = "patient"
    __table_args__ = {"schema": "trustchain"}

    id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    site_name: Mapped[str] = mapped_column(String, nullable=False)
    country: Mapped[str] = mapped_column(String, nullable=False)
    operator_id: Mapped[str] = mapped_column(String, nullable=False)
    patient_pseudonym: Mapped[str] = mapped_column(String, nullable=False)
    sex: Mapped[str] = mapped_column(String, nullable=False)
    year_of_birth: Mapped[int] = mapped_column(nullable=False)
    diagnosis_date: Mapped[str] = mapped_column(String, nullable=False)
    chronic_hbv_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    on_na_therapy: Mapped[bool] = mapped_column(Boolean, default=False)
    bepirovirsen_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    started_bepirovirsen: Mapped[bool] = mapped_column(Boolean, default=False)
    opted_out_secondary_use: Mapped[bool] = mapped_column(Boolean, default=False)
    baseline_hbsag: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    baseline_hbv_dna: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    baseline_alt: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    baseline_ast: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    hbeag_status: Mapped[str] = mapped_column(String, default="unknown")
    bilirubin: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    albumin: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    inr: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ledger_block: Mapped[int] = mapped_column(nullable=False)
    verification_status: Mapped[str] = mapped_column(String, default="verified")
    visit_count: Mapped[int] = mapped_column(default=0)

    visits: Mapped[list["Visit"]] = relationship("Visit", back_populates="patient", lazy="selectin")


class Visit(Base):
    __tablename__ = "visit"
    __table_args__ = {"schema": "trustchain"}

    id: Mapped[str] = mapped_column(String, primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("trustchain.patient.id"), nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    visit_date: Mapped[str] = mapped_column(String, nullable=False)
    visit_type: Mapped[str] = mapped_column(String, nullable=False)
    quantitative_hbsag: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    hbv_dna: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    hbv_dna_detectable: Mapped[bool] = mapped_column(Boolean, default=True)
    alt: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    ast: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    hbeag_status: Mapped[str] = mapped_column(String, default="unknown")
    bilirubin: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    albumin: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    inr: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    on_na_therapy: Mapped[bool] = mapped_column(Boolean, default=False)
    on_bepirovirsen: Mapped[bool] = mapped_column(Boolean, default=False)
    functional_cure_endpoint: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ledger_block: Mapped[int] = mapped_column(nullable=False)
    verification_status: Mapped[str] = mapped_column(String, default="verified")
    dq_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    readiness_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    patient: Mapped["Patient"] = relationship("Patient", back_populates="visits")


class LedgerBlock(Base):
    __tablename__ = "ledger_block"
    __table_args__ = {"schema": "trustchain"}

    block: Mapped[int] = mapped_column(primary_key=True)
    artifact: Mapped[str] = mapped_column(String, nullable=False)
    event: Mapped[str] = mapped_column(String, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    block_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signer: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="verified")
    omop_domain: Mapped[str] = mapped_column(String, default="UNKNOWN")
    submission_id: Mapped[str | None] = mapped_column(String, nullable=True)
    patient_id: Mapped[str | None] = mapped_column(String, nullable=True)
    visit_id: Mapped[str | None] = mapped_column(String, nullable=True)


class Consent(Base):
    __tablename__ = "consent"
    __table_args__ = {"schema": "trustchain"}

    id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    patient_pseudonym: Mapped[str] = mapped_column(String, nullable=False)
    legal_basis: Mapped[str] = mapped_column(String, nullable=False)
    article_9_condition: Mapped[str] = mapped_column(String, nullable=False)
    purpose: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active")
    retention_until: Mapped[str | None] = mapped_column(String, nullable=True)
    residency_region: Mapped[str] = mapped_column(String, default="EU")
    notes: Mapped[str] = mapped_column(Text, default="")


class Permit(Base):
    __tablename__ = "permit"
    __table_args__ = {"schema": "trustchain"}

    id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    permit_id: Mapped[str] = mapped_column(String, nullable=False)
    requesting_organization: Mapped[str] = mapped_column(String, nullable=False)
    purpose_code: Mapped[str] = mapped_column(String, nullable=False)
    expiry_date: Mapped[str] = mapped_column(String, nullable=False)
    issuing_hdab: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="active")


class AccessAudit(Base):
    __tablename__ = "access_audit"
    __table_args__ = {"schema": "trustchain"}

    id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False)
    roles: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    resource_type: Mapped[str] = mapped_column(String, nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String, nullable=True)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    permit_id: Mapped[str | None] = mapped_column(String, nullable=True)
