from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "unfold",
    "apps.core.admin_config.UniversityAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "django_htmx",
    "apps.core",
    "apps.accounts",
    "apps.academics",
    "apps.admissions",
    "apps.finance",
    "apps.content",
    "apps.assistant",
    "apps.website",
    "apps.portal",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "portal:login"
LOGIN_REDIRECT_URL = "portal:dashboard"
LOGOUT_REDIRECT_URL = "portal:login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Admin theme (django-unfold). Color scale derived from the brand tokens in
# static/src/styles.css (--brand-*, --accent-*) so the admin matches the
# public site/portal instead of introducing a second palette.
UNFOLD = {
    "SITE_TITLE": "Smart University Portal",
    "SITE_HEADER": "Smart University Portal Admin",
    "SHOW_LANGUAGES": False,
    "COLORS": {
        "primary": {
            "50": "242 248 246",
            "100": "221 239 232",
            "200": "173 199 191",
            "300": "125 159 150",
            "400": "77 119 109",
            "500": "29 78 66",
            "600": "23 63 54",
            "700": "18 48 42",
            "800": "13 33 30",
            "900": "8 18 18",
            "950": "4 10 10",
        },
    },
    "DASHBOARD_CALLBACK": "apps.core.dashboard.dashboard_callback",
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "contact": env("CONTACT_THROTTLE_RATE", default="5/hour"),
        "ask": env("ASK_THROTTLE_RATE", default="20/hour"),
        # Shared by the JWT login/refresh views and the portal's session
        # login view - keyed by IP for anonymous attempts, so it caps
        # credential-stuffing/brute-force against either auth surface.
        "login": env("LOGIN_THROTTLE_RATE", default="10/hour"),
        "register": env("REGISTER_THROTTLE_RATE", default="5/hour"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_TOKEN_MINUTES", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_TOKEN_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
}

# Assistant app (RAG)
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")

# Document uploads are parsed in-memory (pypdf/python-docx) on ingestion -
# capped so a large or malformed upload can't be used for memory-exhaustion
# DoS against that parsing step.
ASSISTANT_MAX_UPLOAD_SIZE_MB = env.int("ASSISTANT_MAX_UPLOAD_SIZE_MB", default=20)

ASSISTANT_EMBEDDING_CLIENT = env(
    "ASSISTANT_EMBEDDING_CLIENT",
    default="apps.assistant.clients.embeddings.GeminiEmbeddingClient",
)
ASSISTANT_LLM_CLIENT = env(
    "ASSISTANT_LLM_CLIENT", default="apps.assistant.clients.llm.GeminiLLMClient"
)
# Client used ONLY for questions that include a student's own data
# (allow_training=False). Left unset by default so those questions fail
# closed instead of silently going through the training-eligible default
# client - set this only once you have a client/API key/tier that is
# actually verified to exclude prompts from model training.
ASSISTANT_LLM_CLIENT_PRIVATE = env("ASSISTANT_LLM_CLIENT_PRIVATE", default="")
ASSISTANT_EMBEDDING_MODEL = env("ASSISTANT_EMBEDDING_MODEL", default="gemini-embedding-001")
ASSISTANT_EMBEDDING_DIM = env.int("ASSISTANT_EMBEDDING_DIM", default=768)
ASSISTANT_LLM_MODEL = env("ASSISTANT_LLM_MODEL", default="gemini-2.5-flash")

ASSISTANT_CHUNK_TOKENS = env.int("ASSISTANT_CHUNK_TOKENS", default=500)
ASSISTANT_CHUNK_OVERLAP_TOKENS = env.int("ASSISTANT_CHUNK_OVERLAP_TOKENS", default=50)
ASSISTANT_RETRIEVAL_LIMIT = env.int("ASSISTANT_RETRIEVAL_LIMIT", default=6)
# Cosine distance floor for a retrieved chunk to count as relevant. Calibrated
# against gemini-embedding-001: related paraphrases measured ~0.17-0.24,
# unrelated questions ~0.57-0.58, so 0.4 sits safely in the gap.
ASSISTANT_MAX_DISTANCE = env.float("ASSISTANT_MAX_DISTANCE", default=0.4)

# Runs ingestion inline instead of on a background thread; on for tests/dev.
ASSISTANT_INGEST_SYNC = env.bool("ASSISTANT_INGEST_SYNC", default=False)

# Catalog sync (management command sync_catalog_documents): how many rendered
# chunks go into one embed_documents() call, and the pause between calls -
# tuned down against free-tier embedding rate limits rather than for speed.
ASSISTANT_CATALOG_BATCH_SIZE = env.int("ASSISTANT_CATALOG_BATCH_SIZE", default=10)
ASSISTANT_CATALOG_BATCH_DELAY_SECONDS = env.float(
    "ASSISTANT_CATALOG_BATCH_DELAY_SECONDS", default=1.0
)
ASSISTANT_CATALOG_MAX_RETRIES = env.int("ASSISTANT_CATALOG_MAX_RETRIES", default=5)
ASSISTANT_CATALOG_RETRY_BASE_DELAY = env.float(
    "ASSISTANT_CATALOG_RETRY_BASE_DELAY", default=2.0
)
