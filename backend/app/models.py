from sqlalchemy import String, Date, DateTime, Boolean, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
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
