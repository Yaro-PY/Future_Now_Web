DO $future_now_directions$
BEGIN
  SET LOCAL lock_timeout = '5s';
  PERFORM pg_advisory_xact_lock(4854075175168901856);
  CREATE TABLE IF NOT EXISTS public.directions (
    key VARCHAR(32) PRIMARY KEY,
    title_uk VARCHAR(100) NOT NULL,
    title_en VARCHAR(100) NOT NULL,
    description_uk VARCHAR(600) NOT NULL,
    description_en VARCHAR(600) NOT NULL,
    filter_type VARCHAR(16) NOT NULL,
    topic VARCHAR(16),
    cover_version VARCHAR(32),
    cover_content BYTEA,
    revision INTEGER NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
  );
END
$future_now_directions$;
