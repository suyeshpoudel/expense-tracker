from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured


def database_settings(database_url, default_sqlite_path):
    if not database_url:
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": Path(default_sqlite_path),
            }
        }

    parsed = urlsplit(database_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured(
            "DATABASE_URL must use the postgres or postgresql scheme."
        )

    database_name = unquote(parsed.path.removeprefix("/"))
    if not database_name:
        raise ImproperlyConfigured(
            "DATABASE_URL must include a database name."
        )

    try:
        port = parsed.port
    except ValueError as exc:
        raise ImproperlyConfigured(
            "DATABASE_URL contains an invalid port."
        ) from exc

    options = {}
    sslmode = parse_qs(parsed.query).get("sslmode", [None])[0]
    if sslmode:
        options["sslmode"] = sslmode

    config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": database_name,
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(port) if port is not None else "",
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
    if options:
        config["OPTIONS"] = options

    return {"default": config}
