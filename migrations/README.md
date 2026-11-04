# Shared PostgreSQL schema

`001_shared_website.sql` adds the tables and columns required by the current bot and website to the existing PostgreSQL database. It is an alternative to running `setup_database.py` with the same backend `DATABASE_URL`.

In the SQL editor for the existing production database, open a fresh query, paste the entire file, disable Read-only and run it once. The file is one atomic `DO` statement with a schema advisory lock; it can be rerun. A successful run may return no rows. Existing user, opportunity, bookmark and report records are retained. Report metadata and previously unknown price flags are initialized as in `database._migrate`.

After execution, check the website `/health`, which should return `OK`. Publish the matching bot version as well so source imports preserve manual edits and both applications support the shared login.

The generated SQL was exercised twice against empty and legacy-shaped databases in isolated PGlite PostgreSQL tests. These checks do not mean the migration has already been run against Neon. No production connection strings or data are included.

References: [PostgreSQL DO](https://www.postgresql.org/docs/current/sql-do.html), [ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html).


## User controls update

After the base schema, run `002_user_controls.sql` before deploying the user-controls release of both apps. It adds submissions.revision and submissions.updated_at in one atomic, repeatable DO statement and retains existing rows. Do not create a separate database or branch. See [USER_CONTROLS.md](../USER_CONTROLS.md).


## Profile photo and MFA

Run `003_profile_security.sql` after 001/002, then set the same secret `AUTH_ENCRYPTION_KEY` on both production projects before enabling MFA. Existing accounts start with MFA disabled. See [SECURITY_PROFILE.md](../SECURITY_PROFILE.md).
