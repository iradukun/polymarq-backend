from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="U7mZqPkCPqiMdorJwKlThI78yRpLYfyqQiGkakMNsPHA33KiOoc3hnjcOTexNnC1",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
# ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])
ALLOWED_HOSTS = ["*"]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["TEST"] = {"NAME": "development_test_db"}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)  # noqa: F405

# CACHES
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Mimicing memcache behavior.
            # https://github.com/jazzband/django-redis#memcached-exceptions-behavior
            "IGNORE_EXCEPTIONS": True,
        },
    }
}

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/topics/security/#ssl-https
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works
SECURE_HSTS_SECONDS = 60
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool("DJANGO_SECURE_CONTENT_TYPE_NOSNIFF", default=True)

# STATIC
# ------------------------
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# WHITENOISE_MANIFEST_STRICT = False

# MEDIA
# ------------------------------------------------------------------------------


# Your stuff...
# ------------------------------------------------------------------------------

# DJANGO-STORAGES
# ------------------------------------------------------------------------------
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
# aws settings
AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME")
AWS_DEFAULT_ACL = "public-read"
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
AWS_S3_FILE_OVERWRITE = False
AWS_S3_REGION_NAME = "us-east-1"
# s3 public media settings
PUBLIC_MEDIA_LOCATION = "media"
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
# https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = env("EMAIL_HOST", default="mailhog")
# https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = 1025


# SMS
# ------------------------------------------------------------------------------
USE_SMS2EMAILAPI = True
SMS2EMAILAPI_URL = env.str("SMS2EMAILAPI_URL", default="http://polymarq_backend_local_smsapi2email:8080/sms.do")
SMS2EMAILAPI_FROM = env.str("SMS2EMAILAPI_FROM", default="Polymarq")
SMS2EMAILAPI_USERNAME = env.str("SMS2EMAILAPI_USERNAME", default="polymarq-notifier")

# django-rest-framework
# -------------------------------------------------------------------------------
# Tools that generate code samples can use SERVERS to point to the correct domain
SPECTACULAR_SETTINGS["SERVERS"] = [  # noqa: F405
    {"url": "https://dev.polymarqbackend.com", "description": "Development server"},
]
