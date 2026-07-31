-- PostgreSQL schema design for ai_reporting_automation_workspace.
-- Step 7-B design artifact only. Do not execute against production without a
-- reviewed migration plan, backup, staging import, and rollback script.

BEGIN;

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    display_name TEXT NOT NULL,
    email TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    password_digest TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    last_login_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ux_users_username UNIQUE (username),
    CONSTRAINT ck_users_username_not_empty CHECK (btrim(username) <> ''),
    CONSTRAINT ck_users_display_name_not_empty CHECK (btrim(display_name) <> ''),
    CONSTRAINT ck_users_role_not_empty CHECK (btrim(role) <> ''),
    CONSTRAINT ck_users_password_salt_not_empty CHECK (btrim(password_salt) <> ''),
    CONSTRAINT ck_users_password_digest_not_empty CHECK (btrim(password_digest) <> ''),
    CONSTRAINT ck_users_status CHECK (status IN ('active', 'disabled', 'locked')),
    CONSTRAINT ck_users_updated_at CHECK (updated_at >= created_at)
);

CREATE TABLE assets (
    id BIGSERIAL PRIMARY KEY,
    asset_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    public_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    checksum TEXT NOT NULL,
    created_by TEXT NOT NULL,
    brand_id TEXT NOT NULL DEFAULT '',
    business_unit TEXT NOT NULL DEFAULT '',
    platform TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL DEFAULT '',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NULL,
    CONSTRAINT fk_assets_created_by FOREIGN KEY (created_by) REFERENCES users(username),
    CONSTRAINT ck_assets_asset_type_not_empty CHECK (btrim(asset_type) <> ''),
    CONSTRAINT ck_assets_filename_not_empty CHECK (btrim(filename) <> ''),
    CONSTRAINT ck_assets_storage_path_not_empty CHECK (btrim(storage_path) <> ''),
    CONSTRAINT ck_assets_public_path_not_empty CHECK (btrim(public_path) <> ''),
    CONSTRAINT ck_assets_mime_type_not_empty CHECK (btrim(mime_type) <> ''),
    CONSTRAINT ck_assets_size_non_negative CHECK (size_bytes >= 0),
    CONSTRAINT ck_assets_checksum_not_empty CHECK (btrim(checksum) <> ''),
    CONSTRAINT ck_assets_metadata_object CHECK (jsonb_typeof(metadata_json) = 'object'),
    CONSTRAINT ck_assets_expires_at CHECK (expires_at IS NULL OR expires_at >= created_at)
);

CREATE TABLE tasks (
    id BIGSERIAL PRIMARY KEY,
    task_type TEXT NOT NULL,
    task_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_by TEXT NOT NULL,
    owner TEXT NOT NULL,
    brand_id TEXT NOT NULL,
    brand_name TEXT NOT NULL DEFAULT '',
    business_unit TEXT NOT NULL,
    platform TEXT NOT NULL,
    channel TEXT NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    scope_snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    idempotency_key TEXT NOT NULL,
    output_folder TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cancelled_at TIMESTAMPTZ NULL,
    CONSTRAINT ux_tasks_idempotency_key UNIQUE (idempotency_key),
    CONSTRAINT fk_tasks_created_by FOREIGN KEY (created_by) REFERENCES users(username),
    CONSTRAINT fk_tasks_owner FOREIGN KEY (owner) REFERENCES users(username),
    CONSTRAINT ck_tasks_status CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled')),
    CONSTRAINT ck_tasks_task_type_not_empty CHECK (btrim(task_type) <> ''),
    CONSTRAINT ck_tasks_task_name_not_empty CHECK (btrim(task_name) <> ''),
    CONSTRAINT ck_tasks_created_by_not_empty CHECK (btrim(created_by) <> ''),
    CONSTRAINT ck_tasks_owner_not_empty CHECK (btrim(owner) <> ''),
    CONSTRAINT ck_tasks_brand_id_not_empty CHECK (btrim(brand_id) <> ''),
    CONSTRAINT ck_tasks_business_unit_not_empty CHECK (btrim(business_unit) <> ''),
    CONSTRAINT ck_tasks_platform_not_empty CHECK (btrim(platform) <> ''),
    CONSTRAINT ck_tasks_channel_not_empty CHECK (btrim(channel) <> ''),
    CONSTRAINT ck_tasks_payload_object CHECK (jsonb_typeof(payload_json) = 'object'),
    CONSTRAINT ck_tasks_scope_snapshot_object CHECK (jsonb_typeof(scope_snapshot_json) = 'object'),
    CONSTRAINT ck_tasks_idempotency_key_not_empty CHECK (btrim(idempotency_key) <> ''),
    CONSTRAINT ck_tasks_updated_at CHECK (updated_at >= created_at),
    CONSTRAINT ck_tasks_cancelled_at CHECK (cancelled_at IS NULL OR cancelled_at >= created_at),
    CONSTRAINT ck_tasks_cancelled_status CHECK (
        cancelled_at IS NULL OR status = 'cancelled'
    )
);

CREATE TABLE task_runs (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL,
    attempt INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    queue_name TEXT NOT NULL DEFAULT 'default',
    worker_id TEXT NOT NULL DEFAULT '',
    started_at TIMESTAMPTZ NULL,
    finished_at TIMESTAMPTZ NULL,
    error_code TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    progress_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_task_runs_task_id FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    CONSTRAINT ux_task_runs_task_attempt UNIQUE (task_id, attempt),
    CONSTRAINT ck_task_runs_attempt_positive CHECK (attempt > 0),
    CONSTRAINT ck_task_runs_status CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled')),
    CONSTRAINT ck_task_runs_queue_name_not_empty CHECK (btrim(queue_name) <> ''),
    CONSTRAINT ck_task_runs_progress_object CHECK (jsonb_typeof(progress_json) = 'object'),
    CONSTRAINT ck_task_runs_updated_at CHECK (updated_at >= created_at),
    CONSTRAINT ck_task_runs_started_at CHECK (started_at IS NULL OR started_at >= created_at),
    CONSTRAINT ck_task_runs_finished_at CHECK (
        finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at
    ),
    CONSTRAINT ck_task_runs_failed_error CHECK (
        status <> 'failed' OR btrim(error_message) <> '' OR btrim(error_code) <> ''
    )
);

CREATE TABLE task_results (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL,
    run_id BIGINT NULL,
    asset_id BIGINT NULL,
    result_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    public_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    checksum TEXT NOT NULL DEFAULT '',
    summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NULL,
    CONSTRAINT fk_task_results_task_id FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    CONSTRAINT fk_task_results_run_id FOREIGN KEY (run_id) REFERENCES task_runs(id) ON DELETE SET NULL,
    CONSTRAINT fk_task_results_asset_id FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE SET NULL,
    CONSTRAINT ck_task_results_result_type_not_empty CHECK (btrim(result_type) <> ''),
    CONSTRAINT ck_task_results_filename_not_empty CHECK (btrim(filename) <> ''),
    CONSTRAINT ck_task_results_storage_path_not_empty CHECK (btrim(storage_path) <> ''),
    CONSTRAINT ck_task_results_public_path_not_empty CHECK (btrim(public_path) <> ''),
    CONSTRAINT ck_task_results_mime_type_not_empty CHECK (btrim(mime_type) <> ''),
    CONSTRAINT ck_task_results_size_non_negative CHECK (size_bytes >= 0),
    CONSTRAINT ck_task_results_summary_object CHECK (jsonb_typeof(summary_json) = 'object'),
    CONSTRAINT ck_task_results_expires_at CHECK (expires_at IS NULL OR expires_at >= created_at)
);

CREATE TABLE reports (
    id BIGSERIAL PRIMARY KEY,
    module TEXT NOT NULL,
    report_type TEXT NOT NULL,
    title TEXT NOT NULL,
    brand_id TEXT NOT NULL DEFAULT '',
    brand_name TEXT NOT NULL DEFAULT '',
    business_type TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL DEFAULT '',
    task_id BIGINT NULL,
    asset_id BIGINT NULL,
    created_by TEXT NOT NULL,
    summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    warnings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_reports_task_id FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL,
    CONSTRAINT fk_reports_asset_id FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE SET NULL,
    CONSTRAINT fk_reports_created_by FOREIGN KEY (created_by) REFERENCES users(username),
    CONSTRAINT ck_reports_module_not_empty CHECK (btrim(module) <> ''),
    CONSTRAINT ck_reports_report_type_not_empty CHECK (btrim(report_type) <> ''),
    CONSTRAINT ck_reports_title_not_empty CHECK (btrim(title) <> ''),
    CONSTRAINT ck_reports_business_type_not_empty CHECK (btrim(business_type) <> ''),
    CONSTRAINT ck_reports_created_by_not_empty CHECK (btrim(created_by) <> ''),
    CONSTRAINT ck_reports_summary_object CHECK (jsonb_typeof(summary_json) = 'object'),
    CONSTRAINT ck_reports_warnings_array CHECK (jsonb_typeof(warnings_json) = 'array')
);

CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_role ON users(role);

CREATE INDEX idx_assets_type_created_at ON assets(asset_type, created_at DESC);
CREATE INDEX idx_assets_scope ON assets(brand_id, business_unit, platform, channel);
CREATE INDEX idx_assets_created_by ON assets(created_by, created_at DESC);
CREATE INDEX idx_assets_checksum ON assets(checksum);

CREATE INDEX idx_tasks_status_updated_at ON tasks(status, updated_at DESC);
CREATE INDEX idx_tasks_created_by_updated_at ON tasks(created_by, updated_at DESC);
CREATE INDEX idx_tasks_owner_updated_at ON tasks(owner, updated_at DESC);
CREATE INDEX idx_tasks_scope ON tasks(brand_id, business_unit, platform, channel);
CREATE INDEX idx_tasks_type_scope ON tasks(task_type, brand_id, platform, channel);
CREATE INDEX idx_tasks_payload_gin ON tasks USING GIN (payload_json);
CREATE INDEX idx_tasks_scope_snapshot_gin ON tasks USING GIN (scope_snapshot_json);

CREATE INDEX idx_task_runs_task_attempt ON task_runs(task_id, attempt DESC);
CREATE INDEX idx_task_runs_status_created_at ON task_runs(status, created_at DESC);
CREATE INDEX idx_task_runs_worker ON task_runs(worker_id, created_at DESC);
CREATE INDEX idx_task_runs_progress_gin ON task_runs USING GIN (progress_json);

CREATE INDEX idx_task_results_task_created_at ON task_results(task_id, created_at DESC);
CREATE INDEX idx_task_results_run_id ON task_results(run_id);
CREATE INDEX idx_task_results_asset_id ON task_results(asset_id);
CREATE INDEX idx_task_results_summary_gin ON task_results USING GIN (summary_json);

CREATE INDEX idx_reports_brand_created_at ON reports(brand_id, created_at DESC);
CREATE INDEX idx_reports_task_id ON reports(task_id);
CREATE INDEX idx_reports_asset_id ON reports(asset_id);
CREATE INDEX idx_reports_created_by ON reports(created_by, created_at DESC);
CREATE INDEX idx_reports_scope ON reports(brand_id, platform, channel);
CREATE INDEX idx_reports_summary_gin ON reports USING GIN (summary_json);

COMMIT;
