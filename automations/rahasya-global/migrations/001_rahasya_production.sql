BEGIN;

CREATE TABLE IF NOT EXISTS rahasya_projects (
  project_id text PRIMARY KEY,
  channel_key text NOT NULL DEFAULT 'rahasya-global',
  topic text NOT NULL,
  status text NOT NULL,
  current_stage text NOT NULL,
  project jsonb NOT NULL,
  published_video_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rahasya_projects_status_idx
  ON rahasya_projects (status, updated_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS rahasya_projects_video_idx
  ON rahasya_projects (published_video_id)
  WHERE published_video_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS rahasya_events (
  event_key text PRIMARY KEY,
  project_id text NOT NULL REFERENCES rahasya_projects(project_id) ON DELETE CASCADE,
  event_type text NOT NULL,
  stage text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rahasya_events_project_idx
  ON rahasya_events (project_id, created_at DESC);

CREATE TABLE IF NOT EXISTS rahasya_approvals (
  approval_key text PRIMARY KEY,
  project_id text NOT NULL REFERENCES rahasya_projects(project_id) ON DELETE CASCADE,
  gate text NOT NULL,
  decision text NOT NULL CHECK (decision IN ('pending', 'approved', 'rejected')),
  reviewer text,
  notes text,
  release_controls jsonb NOT NULL DEFAULT '{}'::jsonb,
  resume_url text,
  requested_at timestamptz NOT NULL DEFAULT now(),
  decided_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rahasya_approvals_project_idx
  ON rahasya_approvals (project_id, requested_at DESC);

CREATE TABLE IF NOT EXISTS rahasya_rights_provenance (
  project_id text NOT NULL REFERENCES rahasya_projects(project_id) ON DELETE CASCADE,
  asset_key text NOT NULL,
  source_url text,
  license text,
  rights_holder text,
  clearance_status text NOT NULL,
  notes text,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, asset_key)
);

CREATE INDEX IF NOT EXISTS rahasya_rights_status_idx
  ON rahasya_rights_provenance (clearance_status, updated_at DESC);

CREATE TABLE IF NOT EXISTS rahasya_cost_ledger (
  cost_key text PRIMARY KEY,
  project_id text,
  stage text NOT NULL,
  provider text,
  model text,
  request_id text,
  input_tokens bigint,
  output_tokens bigint,
  cost_usd numeric(14, 6) NOT NULL DEFAULT 0,
  latency_ms integer,
  cache_status text,
  fallback text,
  decision text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rahasya_cost_project_idx
  ON rahasya_cost_ledger (project_id, created_at DESC);

CREATE TABLE IF NOT EXISTS rahasya_analytics_snapshots (
  video_id text NOT NULL,
  project_id text REFERENCES rahasya_projects(project_id) ON DELETE SET NULL,
  snapshot_date date NOT NULL,
  metrics jsonb NOT NULL,
  fetched_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (video_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS rahasya_analytics_date_idx
  ON rahasya_analytics_snapshots (snapshot_date DESC, video_id);

CREATE TABLE IF NOT EXISTS rahasya_growth_recommendations (
  recommendation_key text PRIMARY KEY,
  period_start date NOT NULL,
  period_end date NOT NULL,
  recommendations jsonb NOT NULL,
  experiment_plan jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMIT;
