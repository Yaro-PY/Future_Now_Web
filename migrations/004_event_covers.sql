-- Add optional covers to the existing shared Future Now database.
DO $future_now_covers$
BEGIN
  SET LOCAL lock_timeout = '5s';
  PERFORM pg_advisory_xact_lock(4854075175168901856);
  CREATE TABLE IF NOT EXISTS public.event_covers (
    event_id INTEGER PRIMARY KEY REFERENCES public.events(id) ON DELETE CASCADE,
    version VARCHAR(32) NOT NULL,
    content BYTEA NOT NULL
  );
END
$future_now_covers$;
