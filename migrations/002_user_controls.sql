-- Future Now: author proposal controls, additive and repeatable.
-- Run the ENTIRE statement on the existing shared Neon database, Read-only OFF.
DO $future_now_user_controls$
BEGIN
  PERFORM set_config('search_path','public',true);
  PERFORM set_config('lock_timeout','5s',true);
  PERFORM pg_advisory_xact_lock(4854075175168901856);
  ALTER TABLE public.submissions ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1;
  ALTER TABLE public.submissions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;
  UPDATE public.submissions SET updated_at=created_at WHERE updated_at IS NULL;
  ALTER TABLE public.submissions ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;
  ALTER TABLE public.submissions ALTER COLUMN updated_at SET NOT NULL;
END
$future_now_user_controls$;
