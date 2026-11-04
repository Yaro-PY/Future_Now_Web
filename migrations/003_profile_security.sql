-- Future Now: private avatars and optional two-factor authentication.
-- Existing users keep their password and start with 2FA disabled.
-- Run the ENTIRE statement in the existing shared Neon database, Read-only OFF.
DO $future_now_security$
BEGIN
  PERFORM set_config('search_path','public',true);

  PERFORM set_config('lock_timeout','5s',true);

  PERFORM pg_advisory_xact_lock(4854075175168901856);

  ALTER TABLE public.accounts ADD COLUMN IF NOT EXISTS avatar_revision INTEGER NOT NULL DEFAULT 0;

  CREATE TABLE IF NOT EXISTS account_avatars (
    account_id BIGINT NOT NULL,
    content BYTEA NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (account_id),
    FOREIGN KEY(account_id) REFERENCES accounts (telegram_id)
  );

  CREATE TABLE IF NOT EXISTS two_factor (
    credential_id VARCHAR(36) NOT NULL,
    totp_secret TEXT,
    telegram_enabled BOOLEAN NOT NULL,
    recovery_hashes JSON NOT NULL,
    last_totp_step BIGINT NOT NULL,
    revision INTEGER NOT NULL,
    pending_secret TEXT,
    pending_token_hash VARCHAR(64),
    pending_session VARCHAR(64),
    pending_expires TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (credential_id),
    FOREIGN KEY(credential_id) REFERENCES credentials (id)
  );

  CREATE TABLE IF NOT EXISTS auth_challenges (
    token_hash VARCHAR(64) NOT NULL,
    credential_id VARCHAR(36) NOT NULL,
    binding_hash VARCHAR(64) NOT NULL,
    purpose VARCHAR(24) NOT NULL,
    credential_digest VARCHAR(64) NOT NULL,
    factor_revision INTEGER NOT NULL,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    attempts INTEGER NOT NULL,
    consumed BOOLEAN NOT NULL,
    telegram_code_hash VARCHAR(64),
    sent_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (token_hash),
    FOREIGN KEY(credential_id) REFERENCES credentials (id)
  );

  CREATE INDEX IF NOT EXISTS ix_auth_challenges_credential_id ON auth_challenges (credential_id);

  CREATE INDEX IF NOT EXISTS ix_auth_challenges_expires_at ON auth_challenges (expires_at);
END
$future_now_security$;
