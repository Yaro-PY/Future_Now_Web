-- Future Now: shared bot + website schema, 2026-10-29.
-- Additive and repeatable. No records are deleted.
-- Run the ENTIRE block with Read-only disabled in the existing production database.
-- This is one atomic PostgreSQL statement; an error rolls back this block.
DO $future_now_schema$
BEGIN
  PERFORM set_config('search_path','public',true);

  PERFORM set_config('lock_timeout','5s',true);

  PERFORM pg_advisory_xact_lock(4854075175168901856);

  CREATE TABLE IF NOT EXISTS accounts (
    telegram_id BIGINT NOT NULL,
    language VARCHAR(2) NOT NULL,
    profile JSON,
    search_defaults JSON NOT NULL,
    notifications JSON NOT NULL,
    notification_since TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    flow JSON NOT NULL,
    PRIMARY KEY (telegram_id)
  );

  CREATE TABLE IF NOT EXISTS admin_audit (
    id SERIAL NOT NULL,
    entity VARCHAR(20) NOT NULL,
    entity_id INTEGER NOT NULL,
    actor_id BIGINT NOT NULL,
    changes JSON NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id)
  );

  CREATE TABLE IF NOT EXISTS auth_throttles (
    key VARCHAR(64) NOT NULL,
    window_start TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    attempts INTEGER NOT NULL,
    PRIMARY KEY (key)
  );

  CREATE TABLE IF NOT EXISTS catalog_sources (
    key VARCHAR(40) NOT NULL,
    name VARCHAR(200) NOT NULL,
    url VARCHAR(500) NOT NULL,
    last_attempt_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    last_success_at TIMESTAMP WITHOUT TIME ZONE,
    status VARCHAR(20) NOT NULL,
    fetched INTEGER NOT NULL,
    error_code VARCHAR(40) NOT NULL,
    PRIMARY KEY (key)
  );

  CREATE TABLE IF NOT EXISTS events (
    id SERIAL NOT NULL,
    external_id VARCHAR(500) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    url VARCHAR(2000) NOT NULL,
    source VARCHAR(200) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    subjects JSON NOT NULL,
    min_age INTEGER,
    max_age INTEGER,
    start_at TIMESTAMP WITHOUT TIME ZONE,
    deadline TIMESTAMP WITHOUT TIME ZONE,
    is_free BOOLEAN NOT NULL,
    price_text VARCHAR(200) NOT NULL,
    format VARCHAR(50) NOT NULL,
    city VARCHAR(200) NOT NULL,
    raw_text TEXT NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    country VARCHAR(50) NOT NULL,
    topics JSON NOT NULL,
    criteria JSON NOT NULL,
    price_known BOOLEAN NOT NULL,
    organizer VARCHAR(500) NOT NULL,
    participation_language VARCHAR(100) NOT NULL,
    requirements TEXT NOT NULL,
    is_self_paced BOOLEAN NOT NULL,
    is_closed BOOLEAN NOT NULL,
    verified_at TIMESTAMP WITHOUT TIME ZONE,
    revision INTEGER NOT NULL,
    admin_overrides JSON NOT NULL,
    source_url VARCHAR(2000) NOT NULL,
    admin_updated_at TIMESTAMP WITHOUT TIME ZONE,
    admin_updated_by BIGINT,
    PRIMARY KEY (id)
  );

  CREATE TABLE IF NOT EXISTS notification_receipts (
    telegram_id BIGINT NOT NULL,
    key VARCHAR(150) NOT NULL,
    sent_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (telegram_id, key)
  );

  CREATE TABLE IF NOT EXISTS reports (
    id SERIAL NOT NULL,
    telegram_id BIGINT NOT NULL,
    event_id INTEGER,
    category VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL,
    review_note TEXT NOT NULL,
    reviewed_by BIGINT,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    resolved_at TIMESTAMP WITHOUT TIME ZONE,
    revision INTEGER NOT NULL,
    PRIMARY KEY (id)
  );

  CREATE TABLE IF NOT EXISTS saved_events (
    telegram_id BIGINT NOT NULL,
    event_id INTEGER NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (telegram_id, event_id)
  );

  CREATE TABLE IF NOT EXISTS submissions (
    id SERIAL NOT NULL,
    telegram_id BIGINT NOT NULL,
    fingerprint VARCHAR(64) NOT NULL,
    payload JSON NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    reviewed_at TIMESTAMP WITHOUT TIME ZONE,
    reviewed_by BIGINT,
    review_note VARCHAR(500) NOT NULL,
    event_id INTEGER,
    PRIMARY KEY (id),
    UNIQUE (fingerprint)
  );

  CREATE TABLE IF NOT EXISTS subscriptions (
    telegram_id BIGINT NOT NULL,
    event_id INTEGER NOT NULL,
    PRIMARY KEY (telegram_id, event_id)
  );

  CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT NOT NULL,
    age INTEGER,
    subjects JSON NOT NULL,
    time_pref VARCHAR(50) NOT NULL,
    price_pref VARCHAR(50) NOT NULL,
    format_pref VARCHAR(50) NOT NULL,
    PRIMARY KEY (telegram_id)
  );

  CREATE TABLE IF NOT EXISTS credentials (
    id VARCHAR(36) NOT NULL,
    account_id BIGINT NOT NULL,
    nickname VARCHAR(32) NOT NULL,
    password_hash VARCHAR(512) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (account_id),
    FOREIGN KEY(account_id) REFERENCES accounts (telegram_id),
    UNIQUE (nickname)
  );

  CREATE TABLE IF NOT EXISTS web_sessions (
    token_hash VARCHAR(64) NOT NULL,
    credential_id VARCHAR(36) NOT NULL,
    csrf_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (token_hash),
    FOREIGN KEY(credential_id) REFERENCES credentials (id)
  );

  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT '1970-01-01 00:00:00';

  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS country VARCHAR(50) NOT NULL DEFAULT 'ukraine';

  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS topics JSON NOT NULL DEFAULT '[]';

  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS criteria JSON NOT NULL DEFAULT '[]';

  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='events' AND column_name='price_known') THEN
  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS price_known BOOLEAN NOT NULL DEFAULT FALSE;
  UPDATE public.events SET price_known=TRUE WHERE price_text NOT IN ('','Не вказано','Ціна не вказана');
  END IF;

  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS organizer VARCHAR(500) NOT NULL DEFAULT '';

  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS participation_language VARCHAR(100) NOT NULL DEFAULT '';

  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS requirements TEXT NOT NULL DEFAULT '';

  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS is_self_paced BOOLEAN NOT NULL DEFAULT FALSE;

  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS is_closed BOOLEAN NOT NULL DEFAULT FALSE;

  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP;

  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1;

  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS admin_overrides JSON NOT NULL DEFAULT '{}';

  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS source_url VARCHAR(2000) NOT NULL DEFAULT '';

  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS admin_updated_at TIMESTAMP;

  ALTER TABLE public.events ADD COLUMN IF NOT EXISTS admin_updated_by BIGINT;

  ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'new';

  ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS review_note TEXT NOT NULL DEFAULT '';

  ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS reviewed_by BIGINT;

  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='reports' AND column_name='updated_at') THEN
  ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT '1970-01-01 00:00:00';
  UPDATE public.reports SET updated_at=created_at;
  END IF;

  ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP;

  ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1;

  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='telegram_id' AND data_type<>'bigint') THEN
  ALTER TABLE public.users ALTER COLUMN telegram_id TYPE BIGINT;
  END IF;

  CREATE INDEX IF NOT EXISTS ix_admin_audit_entity ON admin_audit (entity);

  CREATE INDEX IF NOT EXISTS ix_admin_audit_entity_id ON admin_audit (entity_id);

  CREATE UNIQUE INDEX IF NOT EXISTS ix_events_external_id ON events (external_id);

  CREATE INDEX IF NOT EXISTS ix_reports_status ON reports (status);

  CREATE INDEX IF NOT EXISTS ix_submissions_status ON submissions (status);

  CREATE INDEX IF NOT EXISTS ix_submissions_telegram_id ON submissions (telegram_id);

  CREATE INDEX IF NOT EXISTS ix_web_sessions_credential_id ON web_sessions (credential_id);

  CREATE INDEX IF NOT EXISTS ix_web_sessions_expires_at ON web_sessions (expires_at);

  RAISE NOTICE 'Future Now schema is ready. Existing records were retained.';
END
$future_now_schema$;
