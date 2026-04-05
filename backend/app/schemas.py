from pydantic import BaseModel
from datetime import datetime, date


class SnapshotOut(BaseModel):
    snapshot_id: str
    snapshot_label: str
    omop_release_date: date
    cdm_version: str
    etl_version: str
    status: str


class PipelineRunOut(BaseModel):
    run_id: str
    snapshot_id: str
    source_system: str
    started_at: datetime
    finished_at: datetime | None = None
    run_status: str
    dq_score: float | None = None
    critical_issue_count: int


class QualityIssueOut(BaseModel):
    issue_id: str
    run_id: str
    issue_code: str
    severity: str
    omop_table: str | None = None
    omop_field: str | None = None
    affected_count: int | None = None
    issue_summary: str
    status: str
