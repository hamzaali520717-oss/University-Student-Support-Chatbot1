from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE, env

DEBUG = False

MIDDLEWARE = MIDDLEWARE[:1] + ["whitenoise.middleware.WhiteNoiseMiddleware"] + MIDDLEWARE[1:]

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env("MEDIA_BUCKET_NAME"),
            "endpoint_url": env("MEDIA_ENDPOINT_URL"),
            "access_key": env("MEDIA_ACCESS_KEY"),
            "secret_key": env("MEDIA_SECRET_KEY"),
            "default_acl": None,
            "querystring_auth": True,
        },
    },
}

SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Render (and Railway) terminate TLS at a proxy and forward plain HTTP -
# without this, SECURE_SSL_REDIRECT above causes an infinite redirect loop.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Required for session-based CSRF (the portal login form) once served over
# HTTPS behind the platform's domain - Django checks Origin/Referer against
# this list for unsafe methods.
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS")

# ScopedRateThrottle (login/register/contact/ask, see apps.accounts.views /
# apps.portal.views) reads Django's default cache. LocMemCache is
# per-process, so with >1 gunicorn worker the throttle limit would silently
# multiply by worker count - a shared Redis cache keeps it correct.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
    }
}
