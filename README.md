# Smart University Portal

A university platform built around one shared PostgreSQL database: a public
website, a student portal, and an admin dashboard, plus an AI Campus
Assistant that answers questions from university documents and live database
content using retrieval-augmented generation (RAG).

## Stack

- **Backend** — Django + Django REST Framework, API under `/api/v1/`
- **Database** — PostgreSQL with the `pgvector` extension
- **Auth** — `djangorestframework-simplejwt`; one custom `User` with a
  `role` field (`student` / `admin`)
- **Frontend** — Django templates + Tailwind CSS + Flowbite + HTMX (no SPA
  framework)
- **AI** — RAG over `pgvector`, provider-agnostic LLM client (default:
  Google Gemini 2.5 Flash)
- **Infra** — Docker + docker-compose locally; see [LAUNCH.md](LAUNCH.md)
  for production (Render)

## Key features

- **Three surfaces, one database** — the public website, the student
  portal, and the admin dashboard all read and write the same PostgreSQL
  database instead of syncing across separate systems.
- **AI Campus Assistant, two-path privacy design** — general questions
  (admissions, programs, policies) go to the default, training-eligible LLM
  client. Any question touching a student's own data (fees, grades,
  attendance) is routed to a separate client verified to exclude prompts
  from model training — and if that client isn't configured, the assistant
  **fails closed** and refuses to answer rather than falling back to the
  default client.
- **Group-based admin permissions** — `role=admin` users get access through
  an "Admin Staff" Django group, auto-synced to every app's permissions on
  each `migrate`, rather than through `is_superuser`. `is_superuser` is kept
  reserved for the permission system itself, so an admin account can never
  grant itself superuser access through the admin UI.

## Running locally

```bash
cp .env.example .env       # fill in DJANGO_SECRET_KEY, GEMINI_API_KEY, etc.
docker compose up --build
```

This starts Postgres (with `pgvector` baked in), the Django dev server at
`http://localhost:8000`, and a Tailwind watcher for CSS. Run migrations and
create your first admin in a separate shell:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

(`createsuperuser` bypasses the group-based admin path above — fine for
local development, but promote a real `role=admin` account through
`/admin/` before treating it as your day-to-day account.)

## Running tests

Tests use stub LLM/embedding clients, so the full suite runs offline with no
API calls or cost:

```bash
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test web python manage.py test
```

## Deploying

See [LAUNCH.md](LAUNCH.md) for the full production setup on Render —
environment variables, `render.yaml`, the first-admin bootstrap step, and
the scheduled maintenance jobs.
