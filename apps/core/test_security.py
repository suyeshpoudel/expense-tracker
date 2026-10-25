import os
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string
from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse

from config.database import database_settings


class SecurityHeaderTests(SimpleTestCase):
    def test_home_response_sets_security_headers(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(
            response.headers["Referrer-Policy"],
            "strict-origin-when-cross-origin",
        )
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(
            response.headers["Cross-Origin-Opener-Policy"],
            "same-origin",
        )

    @override_settings(
        SECURE_HSTS_SECONDS=3600,
        SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
        SECURE_HSTS_PRELOAD=True,
    )
    def test_hsts_header_uses_configured_values(self):
        response = self.client.get(reverse("core:home"), secure=True)

        self.assertEqual(
            response.headers["Strict-Transport-Security"],
            "max-age=3600; includeSubDomains; preload",
        )


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
class ErrorPageTests(SimpleTestCase):
    def test_missing_page_uses_custom_404_template(self):
        response = self.client.get("/missing-page/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Page not found", status_code=404)

    def test_csrf_failure_uses_custom_403_template(self):
        client = Client(enforce_csrf_checks=True)

        response = client.post(reverse("accounts:logout"))

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403_csrf.html")
        self.assertContains(response, "Security check failed", status_code=403)

    def test_error_templates_render(self):
        expectations = {
            "400.html": "Bad request",
            "403.html": "Permission denied",
            "403_csrf.html": "Security check failed",
            "404.html": "Page not found",
            "500.html": "Something went wrong",
        }

        for template_name, heading in expectations.items():
            with self.subTest(template=template_name):
                content = render_to_string(template_name)
                self.assertIn(heading, content)


class DeploymentSettingsTests(SimpleTestCase):
    base_environment = {
        "DJANGO_DEBUG": "false",
        "DJANGO_SECRET_KEY": (
            "production-check-secret-key-that-is-long-enough-1234567890"
        ),
        "DJANGO_ALLOWED_HOSTS": "example.com",
    }

    def run_manage_check(self, remove=(), **overrides):
        environment = os.environ.copy()
        for name in (
            "DATABASE_URL",
            "DJANGO_ALLOWED_HOSTS",
            "DJANGO_CSRF_COOKIE_SECURE",
            "DJANGO_CSRF_TRUSTED_ORIGINS",
            "DJANGO_DEBUG",
            "DJANGO_LOG_LEVEL",
            "DJANGO_SECRET_KEY",
            "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
            "DJANGO_SECURE_HSTS_PRELOAD",
            "DJANGO_SECURE_HSTS_SECONDS",
            "DJANGO_SECURE_SSL_REDIRECT",
            "DJANGO_SESSION_COOKIE_SECURE",
            "DJANGO_TRUST_X_FORWARDED_PROTO",
        ):
            environment.pop(name, None)
        environment.update(self.base_environment)
        for name in remove:
            environment.pop(name, None)
        environment.update(overrides)

        return subprocess.run(
            [sys.executable, "manage.py", "check", "--deploy"],
            cwd=settings.BASE_DIR,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def test_deploy_check_passes_with_production_settings(self):
        result = self.run_manage_check()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no issues", result.stdout)

    def test_production_requires_a_secret_key(self):
        result = self.run_manage_check(remove=("DJANGO_SECRET_KEY",))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY", result.stderr)

    def test_production_requires_allowed_hosts(self):
        result = self.run_manage_check(remove=("DJANGO_ALLOWED_HOSTS",))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_ALLOWED_HOSTS", result.stderr)

    def test_invalid_boolean_setting_fails_fast(self):
        result = self.run_manage_check(DJANGO_DEBUG="sometimes")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "DJANGO_DEBUG must be a boolean value.",
            result.stderr,
        )


class DatabaseSettingsTests(SimpleTestCase):
    def test_missing_database_url_uses_sqlite(self):
        databases = database_settings(None, Path("/tmp/test.sqlite3"))

        self.assertEqual(
            databases["default"]["ENGINE"],
            "django.db.backends.sqlite3",
        )
        self.assertEqual(
            databases["default"]["NAME"],
            Path("/tmp/test.sqlite3"),
        )

    def test_postgres_url_is_parsed(self):
        databases = database_settings(
            "postgresql://user:p%40ss@db.example.com:5432/expenses"
            "?sslmode=require",
            Path("/tmp/test.sqlite3"),
        )

        config = databases["default"]
        self.assertEqual(
            config["ENGINE"],
            "django.db.backends.postgresql",
        )
        self.assertEqual(config["NAME"], "expenses")
        self.assertEqual(config["USER"], "user")
        self.assertEqual(config["PASSWORD"], "p@ss")
        self.assertEqual(config["HOST"], "db.example.com")
        self.assertEqual(config["PORT"], "5432")
        self.assertEqual(config["OPTIONS"], {"sslmode": "require"})
        self.assertEqual(config["CONN_MAX_AGE"], 60)
        self.assertTrue(config["CONN_HEALTH_CHECKS"])

    def test_unsupported_database_scheme_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            database_settings(
                "mysql://user:password@db.example.com/expenses",
                Path("/tmp/test.sqlite3"),
            )

    def test_database_name_is_required(self):
        with self.assertRaises(ImproperlyConfigured):
            database_settings(
                "postgresql://user:password@db.example.com/",
                Path("/tmp/test.sqlite3"),
            )

    def test_invalid_database_port_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            database_settings(
                "postgresql://user:password@db.example.com:not-a-port/expenses",
                Path("/tmp/test.sqlite3"),
            )
