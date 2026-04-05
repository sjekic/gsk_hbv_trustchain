CREATE SCHEMA IF NOT EXISTS trustchain;

CREATE TABLE IF NOT EXISTS trustchain.dataset_snapshot (
    snapshot_id UUID PRIMARY KEY,
    snapshot_label TEXT NOT NULL,
    omop_release_date DATE NOT NULL,
    cdm_version TEXT NOT NULL,
    vocabulary_version TEXT,
    source_release_date DATE,
    row_count BIGINT,
    manifest_sha256 TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL,
    etl_version TEXT NOT NULL,
    validation_report_uri TEXT,
    status TEXT NOT NULL CHECK (status IN ('draft','validated','released','superseded'))
);

CREATE TABLE IF NOT EXISTS trustchain.pipeline_run (
    run_id UUID PRIMARY KEY,
    snapshot_id UUID REFERENCES trustchain.dataset_snapshot(snapshot_id),
    source_system TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    run_status TEXT NOT NULL CHECK (run_status IN ('running','succeeded','failed','partially_succeeded')),
    schema_check_passed BOOLEAN NOT NULL DEFAULT FALSE,
    linkage_performed BOOLEAN NOT NULL DEFAULT FALSE,
    dq_score NUMERIC(5,2),
    critical_issue_count INTEGER NOT NULL DEFAULT 0,
    signed_by TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS trustchain.artifact_notary (
    artifact_id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES trustchain.pipeline_run(run_id),
    artifact_type TEXT NOT NULL,
    artifact_uri TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    fabric_tx_id TEXT,
    fabric_channel TEXT,
    notarized_at TIMESTAMPTZ,
    signer_msp_id TEXT,
    verification_status TEXT NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending','verified','failed'))
);

CREATE TABLE IF NOT EXISTS trustchain.data_quality_issue (
    issue_id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES trustchain.pipeline_run(run_id),
    issue_code TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('low','medium','high','critical')),
    omop_table TEXT,
    omop_field TEXT,
    affected_count BIGINT,
    issue_summary TEXT NOT NULL,
    issue_detail JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','accepted','resolved'))
);

CREATE TABLE IF NOT EXISTS trustchain.model_registry (
    model_id UUID PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    intended_use TEXT NOT NULL,
    training_data_snapshot_id UUID REFERENCES trustchain.dataset_snapshot(snapshot_id),
    validation_metrics JSONB NOT NULL,
    approval_status TEXT NOT NULL CHECK (approval_status IN ('draft','validated','approved','retired')),
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    model_card_uri TEXT
);

CREATE TABLE IF NOT EXISTS trustchain.processing_registry (
    processing_id UUID PRIMARY KEY,
    purpose_code TEXT NOT NULL,
    lawful_basis TEXT NOT NULL,
    article9_condition TEXT,
    controller_name TEXT NOT NULL,
    processor_name TEXT,
    transfer_restrictions TEXT,
    retention_rule TEXT NOT NULL,
    dpia_reference TEXT,
    effective_from DATE NOT NULL,
    effective_to DATE
);
