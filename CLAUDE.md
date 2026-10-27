Project

Smart University Portal: a public website, a student portal, and an admin dashboard sharing one PostgreSQL database, plus an AI Campus Assistant (RAG) that answers questions from university documents and database content.

Stack


Backend: Django + Django REST Framework, API under /api/v1/.
Database: PostgreSQL with the pgvector extension.
Auth: djangorestframework-simplejwt, one custom User with a role field (student, admin).
Frontend: Django templates + Tailwind CSS + Flowbite components + HTMX. No React.
AI: RAG using pgvector for search and a provider-agnostic LLM client (default Google Gemini 2.5 Flash).
Infra: Docker + docker-compose.


Layout


config/ with split settings (base/dev/prod/test).
apps/ with domain apps: core, accounts, academics, admissions, finance, content, assistant.
requirements/ split into base/dev/prod.


Architecture rules (must follow)


Per app: models.py (data only), selectors.py (all reads), services.py (all writes/logic), serializers.py, permissions.py, thin views.py, urls.py, tests/.
Views never touch the database directly and never hold business logic. Views validate input, call a selector or service, return the result.
Services are functions with keyword-only args; wrap multi-write services in transaction.atomic.
All models inherit a shared BaseModel (created_at, updated_at) from core.
Custom User in accounts must exist before the first migration. Set AUTH_USER_MODEL = "accounts.User".
Read all config and secrets from environment variables. No hardcoded secrets.
Every endpoint ships with tests in the same change.
For the AI assistant, tests use stub LLM/embedding clients so they run offline and free.


UI and design rules


Use the frontend-design and ui-ux-pro-max skills for all UI work.
Never use Inter, Roboto, Arial, or system fonts. Pick a characterful display font and a clean body font.
Commit to ONE dominant brand color plus one accent. All colors in CSS variables. No purple-to-blue gradients on white.
8px spacing rhythm, strong type hierarchy, not borders everywhere. No three-rounded-card hero, no centered-everything.
Use Flowbite (Tailwind) components as the foundation; do not hand-roll what exists.
After any UI change, take a screenshot and compare before saying it's done.
