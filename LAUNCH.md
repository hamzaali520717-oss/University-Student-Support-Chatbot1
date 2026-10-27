# Launch Notes

## Resolved: first-admin bootstrap path

Previously tracked here as an open Phase 3.3 decision (no `seed_admin` /
`bootstrap_admin` command existed; the only ways in were `createsuperuser`,
which bypasses `sync_admin_access` and leaves `role=student`, or promoting a
user through `UserAdmin`, which needs an existing admin session already).

**Decision taken:** added `apps.accounts.services.bootstrap_admin` and the
`bootstrap_admin` management command
(`apps/accounts/management/commands/bootstrap_admin.py`). It creates (or
finds) a user by `BOOTSTRAP_ADMIN_USERNAME`, sets `role=admin`, and runs it
through the same `sync_admin_access` path `UserAdmin` uses — group
membership, `is_staff`, `AdminProfile` — without ever setting
`is_superuser`. Safe to rerun; only sets the password on first creation, so a
later credential rotation can't be undone by rerunning it. See step 7 below
for how it's actually invoked on Render.

---

# Deploying to Render

## 1. Provision the database
1. Apply `render.yaml` via Render's Blueprints UI (or create
   `university-portal-db`, Postgres 16, manually first if you want to run
   step 2 before anything else deploys).
2. Open the database's shell (Render dashboard → the DB → "Connect") and run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
   Must happen before the first `migrate` — `assistant_documentchunk` has a
   `vector` column.

## 2. Set the secrets Render can't generate for you
Marked `sync: false` in `render.yaml` — Render prompts for these on first
blueprint sync, or set them in the dashboard afterward.

| Variable | Used by | Notes |
|---|---|---|
| `DJANGO_ALLOWED_HOSTS` | web, both cron jobs | e.g. `university-portal.onrender.com` (comma-separated if you add a custom domain) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | web, both cron jobs | e.g. `https://university-portal.onrender.com` — must include the scheme |
| `GEMINI_API_KEY` | web, both cron jobs | free-tier Gemini key; assistant answers fail without it |
| `MEDIA_BUCKET_NAME` | web, both cron jobs | your Cloudflare R2 bucket name |
| `MEDIA_ENDPOINT_URL` | web, both cron jobs | R2 S3-compatible endpoint, e.g. `https://<account-id>.r2.cloudflarestorage.com` |
| `MEDIA_ACCESS_KEY` | web, both cron jobs | R2 access key ID |
| `MEDIA_SECRET_KEY` | web, both cron jobs | R2 secret access key |
| `BOOTSTRAP_ADMIN_USERNAME` | web only | username for your first admin login |
| `BOOTSTRAP_ADMIN_EMAIL` | web only | email for that account |
| `BOOTSTRAP_ADMIN_PASSWORD` | web only | temporary password — change it from the admin's own account once in |

Why the cron jobs need `DJANGO_CSRF_TRUSTED_ORIGINS`/`MEDIA_*`/`GEMINI_API_KEY`
even though they never serve HTTP or touch media: all three processes import
the same `config.settings.prod` module, and that module reads these at
import time regardless of which management command actually runs. Missing
any of them crashes the process on startup, not just the web service.

## 3. Env vars already wired up in render.yaml (no action needed)
`DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY` (auto-generated, shared across
services in one blueprint sync), `ASSISTANT_LLM_CLIENT_PRIVATE` (left empty
on purpose — personal questions stay template-only and fail closed rather
than hitting a paid non-training LLM tier), `DATABASE_URL` (from the
Postgres service), `REDIS_URL` (from the Key Value service).

## 4. Optional env vars (defaults are fine unless you need to change them)
`JWT_ACCESS_TOKEN_MINUTES` (15), `JWT_REFRESH_TOKEN_DAYS` (7),
`ASK_THROTTLE_RATE` (20/hour), `CONTACT_THROTTLE_RATE` (5/hour),
`LOGIN_THROTTLE_RATE` (10/hour), `REGISTER_THROTTLE_RATE` (5/hour),
`ASSISTANT_EMBEDDING_MODEL`, `ASSISTANT_EMBEDDING_DIM`, `ASSISTANT_LLM_MODEL`,
`ASSISTANT_MAX_UPLOAD_SIZE_MB`, `ASSISTANT_CHUNK_TOKENS`,
`ASSISTANT_RETRIEVAL_LIMIT`, `ASSISTANT_MAX_DISTANCE`. Do **not** set
`ASSISTANT_INGEST_SYNC` — it must stay `False` in production (it's a
test/dev-only synchronous-ingestion switch).

## 5. Not needed in production
`POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` from `.env.example`
only configure the local docker-compose Postgres container — Render's
managed Postgres provides `DATABASE_URL` directly.

## 6. Deploy
Push to the branch Render is watching. The web service's `preDeployCommand`
(`python manage.py migrate`) runs and must succeed before traffic cuts over;
`collectstatic` + gunicorn start from the Dockerfile's `CMD`.

## 7. Create your admin account (first deploy only, but safe to rerun)

**Primary method — Render CLI (no shell on the host):**
```
render jobs create university-portal-web --start-command "python manage.py bootstrap_admin"
```
Watch it finish in the Render dashboard → web service → Jobs tab.

**Fallback — if `render jobs create` isn't available on your plan/CLI version:**
Guaranteed to work, using nothing but the feature already relied on for
migrations:
1. In `render.yaml`, temporarily change the web service's `preDeployCommand` to:
   ```yaml
   preDeployCommand: python manage.py migrate && python manage.py bootstrap_admin
   ```
2. Push/sync the blueprint. The next deploy runs it once before cutting over traffic.
3. Revert `preDeployCommand` back to `python manage.py migrate` and push
   again, so `bootstrap_admin` doesn't run on every future deploy.

Either path is safe to repeat — rerunning `bootstrap_admin` re-promotes the
same user to `role=admin` but never touches its password, so running it
twice by accident can't lock you out or reset a credential you've since
changed.

## 8. Confirm the two maintenance jobs are scheduled
- **`university-portal-recover-stuck-ingestions`** — every 15 minutes. Marks
  any document ingestion that was killed mid-flight (e.g. by this same
  deploy replacing the web container) as `FAILED` so it can be reindexed.
  There's no separate ingestion worker to babysit — ingestion runs as a
  background thread inside the web process
  (`apps/assistant/services/ingestion.py`), so this job is the only thing
  that recovers from an interrupted one.
- **`university-portal-embedding-drift-check`** — daily. Runs `manage.py
  check --tag assistant_embedding`, which runs *only*
  `apps.assistant.checks.check_embedding_dimension_matches_column` and fails
  (non-zero exit) if `ASSISTANT_EMBEDDING_DIM` no longer matches the
  database column width. Confirm your alerting actually notices a failed
  Render cron run before relying on this.

## 9. Smoke test
- Log in as a student — confirms HTTPS redirect, CSRF, and cookies all agree.
- Upload a document as admin, confirm it reaches `INDEXED` — confirms R2 and
  the ingestion thread both work.
- Ask the assistant a public question — confirms `GEMINI_API_KEY`.
- Ask it something personal — confirms it fails closed rather than erroring.
