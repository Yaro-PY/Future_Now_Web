-- Keep submitted covers private until the corresponding proposal is approved.
DO $future_now_proposal_covers$
BEGIN
  SET LOCAL lock_timeout = '5s';
  PERFORM pg_advisory_xact_lock(4854075175168901856);
  CREATE TABLE IF NOT EXISTS public.submission_covers (
    submission_id INTEGER PRIMARY KEY REFERENCES public.submissions(id) ON DELETE CASCADE,
    version VARCHAR(32) NOT NULL,
    content BYTEA NOT NULL
  );

  CREATE OR REPLACE FUNCTION public.finalize_submission_cover() RETURNS trigger
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp
    AS $finalize_cover$
    BEGIN
      IF NEW.status = 'approved' AND NEW.event_id IS NOT NULL THEN
        INSERT INTO public.event_covers (event_id, version, content)
          SELECT NEW.event_id, version, content FROM public.submission_covers
          WHERE submission_id = NEW.id
          ON CONFLICT (event_id) DO NOTHING;
      END IF;
      DELETE FROM public.submission_covers WHERE submission_id = NEW.id;
      RETURN NEW;
    END;
    $finalize_cover$;

  REVOKE EXECUTE ON FUNCTION public.finalize_submission_cover() FROM PUBLIC;

  DROP TRIGGER IF EXISTS finalize_submission_cover ON public.submissions;
  CREATE TRIGGER finalize_submission_cover AFTER UPDATE OF status ON public.submissions
    FOR EACH ROW
    WHEN (OLD.status = 'pending' AND NEW.status IN ('approved', 'rejected', 'withdrawn'))
    EXECUTE FUNCTION public.finalize_submission_cover();
END
$future_now_proposal_covers$;
