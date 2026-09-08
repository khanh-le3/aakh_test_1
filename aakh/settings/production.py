import os

from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False


def require_env(name):
    """Return an environment variable, or fail loudly at startup if it is missing.

    Production must never fall back to a default for these: a missing SECRET_KEY
    silently weakens every signed cookie and token, and a missing ALLOWED_HOSTS
    would leave the site open to Host header attacks.
    """
    try:
        return os.environ[name]
    except KeyError:
        raise ImproperlyConfigured(
            f"The {name} environment variable must be set when using production settings."
        ) from None


SECRET_KEY = require_env("SECRET_KEY")

# Comma-separated list, e.g. "aakh.org.au,www.aakh.org.au"
ALLOWED_HOSTS = [host.strip() for host in require_env("ALLOWED_HOSTS").split(",") if host.strip()]

# Wagtail uses this to build absolute URLs in notification emails and previews.
WAGTAILADMIN_BASE_URL = require_env("WAGTAILADMIN_BASE_URL")

CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]

# HTTPS / cookie hardening. Behind a load balancer that terminates TLS (e.g. an
# AWS ALB), the app only sees HTTP, so trust the forwarded proto header it sets.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS tells browsers to only ever use HTTPS for this domain. Start at one year
# only once you are confident every subdomain is served over HTTPS.
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ManifestStaticFilesStorage is recommended in production, to prevent
# outdated JavaScript / CSS assets being served from cache
# (e.g. after a Wagtail upgrade).
# See https://docs.djangoproject.com/en/5.2/ref/contrib/staticfiles/#manifeststaticfilesstorage
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

try:
    from .local import *
except ImportError:
    pass
