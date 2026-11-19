"""Load settings against synthetic environments without reading the real .env."""

import os
import runpy
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key
from django.test import SimpleTestCase


class EnvironmentSecurityTests(SimpleTestCase):
    def load_settings(self, **env):
        with patch.dict(os.environ, env, clear=True), patch("dotenv.load_dotenv"):
            return runpy.run_path(str(Path(__file__).with_name("settings.py")))

    def production(self, **overrides):
        env = {
            "DJANGO_ENV": "production", "SECRET_KEY": get_random_secret_key(),
            "ALLOWED_HOSTS": "api.example.com",
        }
        env.update(overrides)
        return self.load_settings(**env)

    def test_development_keeps_existing_local_frontend_and_http(self):
        cfg = self.load_settings()
        self.assertEqual(cfg["DJANGO_ENV"], "development")
        self.assertTrue(cfg["DEBUG"])
        self.assertIn("localhost", cfg["ALLOWED_HOSTS"])
        self.assertIn("http://localhost:5500", cfg["CORS_ALLOWED_ORIGINS"])
        for setting in ("SECURE_SSL_REDIRECT", "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE"):
            self.assertFalse(cfg[setting])
        self.assertGreaterEqual(len(cfg["SECRET_KEY"]), 50)
        self.assertNotEqual(cfg["SECRET_KEY"], self.load_settings()["SECRET_KEY"])

    def test_explicit_development_secret_and_debug_false_are_supported(self):
        key = get_random_secret_key()
        cfg = self.load_settings(SECRET_KEY=key, DEBUG="false")
        self.assertEqual(cfg["SECRET_KEY"], key)
        self.assertFalse(cfg["DEBUG"])
        self.assertFalse(cfg["SECURE_SSL_REDIRECT"])

    def test_production_defaults_to_https_secure_cookies_no_dev_origins(self):
        cfg = self.production()
        self.assertFalse(cfg["DEBUG"])
        self.assertEqual(cfg["ALLOWED_HOSTS"], ["api.example.com"])
        self.assertEqual(cfg["CORS_ALLOWED_ORIGINS"], [])
        self.assertEqual(cfg["CSRF_TRUSTED_ORIGINS"], [])
        self.assertFalse(cfg["CORS_ALLOW_ALL_ORIGINS"])
        self.assertNotIn("SECURE_PROXY_SSL_HEADER", cfg)
        for setting in ("SECURE_SSL_REDIRECT", "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE", "SECURE_CONTENT_TYPE_NOSNIFF"):
            self.assertTrue(cfg[setting])
        self.assertGreater(cfg["SECURE_HSTS_SECONDS"], 0)
        self.assertFalse(cfg["SECURE_HSTS_PRELOAD"])
        self.assertFalse(cfg["SECURE_HSTS_INCLUDE_SUBDOMAINS"])

    def test_production_refuses_missing_or_weak_secret(self):
        for key in ("", "short", "x" * 60, "django-insecure-" + "abcde" * 15):
            with self.subTest(length=len(key)), self.assertRaises(ImproperlyConfigured):
                self.production(SECRET_KEY=key)

    def test_production_refuses_debug_and_missing_or_wildcard_hosts(self):
        for override in ({"DEBUG": "true"}, {"ALLOWED_HOSTS": ""}, {"ALLOWED_HOSTS": "*"}, {"ALLOWED_HOSTS": "https://api.example.com"}):
            with self.subTest(override=override), self.assertRaises(ImproperlyConfigured):
                self.production(**override)

    def test_explicit_https_cors_csrf_and_trusted_proxy(self):
        cfg = self.production(
            CORS_ALLOWED_ORIGINS="https://app.example.com, https://other.example.com:8443",
            CSRF_TRUSTED_ORIGINS="https://app.example.com", TRUST_PROXY_HTTPS="true",
        )
        self.assertEqual(len(cfg["CORS_ALLOWED_ORIGINS"]), 2)
        self.assertEqual(cfg["CSRF_TRUSTED_ORIGINS"], ["https://app.example.com"])
        self.assertEqual(cfg["SECURE_PROXY_SSL_HEADER"], ("HTTP_X_FORWARDED_PROTO", "https"))

    def test_production_rejects_http_wildcard_and_malformed_origins(self):
        for origin in (
            "*", "http://app.example.com", "https://*.example.com", "https://app.example.com/path",
            "https://user:password@app.example.com", "https://app.example.com:bad", "https://[invalid",
        ):
            for name in ("CORS_ALLOWED_ORIGINS", "CSRF_TRUSTED_ORIGINS"):
                with self.subTest(origin=origin, setting=name), self.assertRaises(ImproperlyConfigured):
                    self.production(**{name: origin})

    def test_invalid_environment_bool_and_hsts_fail_closed(self):
        for override in (
            {"DJANGO_ENV": "prodution"}, {"DEBUG": "yes"}, {"TRUST_PROXY_HTTPS": "yes"},
            {"SECURE_HSTS_SECONDS": "invalid"}, {"SECURE_HSTS_SECONDS": "-1"},
            {"SECURE_HSTS_SECONDS": "0"},
        ):
            with self.subTest(override=override), self.assertRaises(ImproperlyConfigured):
                self.production(**override)

    def test_private_root_is_absolute_external_and_storage_has_no_public_backend(self):
        cfg = self.production()
        self.assertTrue(cfg["PRIVATE_RESUME_ROOT"].is_absolute())
        self.assertFalse(cfg["PRIVATE_RESUME_ROOT"].is_relative_to(cfg["BASE_DIR"].parent))
        self.assertEqual(cfg["STORAGES"]["default"]["BACKEND"], "resumes.storage.PrivateResumeStorage")
        self.assertEqual(cfg["MEDIA_ROOT"], cfg["BASE_DIR"] / "media")

    def test_unsafe_or_overlapping_private_root_is_rejected(self):
        backend = Path(__file__).resolve().parent.parent
        for private in ("relative/path", str(backend / "media"), str(backend / "staticfiles"), str(backend / "private")):
            with self.subTest(path=private), self.assertRaises(ImproperlyConfigured):
                self.production(PRIVATE_RESUME_ROOT=private)
        with self.assertRaises(ImproperlyConfigured):
            self.production(LEGACY_RESUME_ROOT=str(backend / "staticfiles" / "legacy"))
        with self.assertRaises(ImproperlyConfigured):
            self.production(LEGACY_RESUME_ROOT="relative/legacy")
