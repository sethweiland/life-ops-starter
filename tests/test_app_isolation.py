"""The Flask app boots on life-ops code only — no meme pipeline imports."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import tests.bootstrap  # noqa: F401

from src.core.tenant import load_tenant_from_path, reset_tenant
from src.core.project_board import reset_project_board
from src.core.s3_store import reset_s3_store
from src.core.tech_spend import reset_tech_spend
from web import create_app

_MEME_PIPELINE_MODULES = (
    "src.core.meme_generator",
    "src.core.pipeline",
    "src.core.two_stage",
    "src.core.rag",
    "src.core.vectorstore",
    "src.core.retriever",
    "src.core.trending_templates",
    "src.core.instagram_publisher",
    "src.core.video_pipeline",
    "src.core.video_composer",
    "src.config",
    "web.blueprints.dashboard",
    "web.blueprints.generate",
    "web.blueprints.gallery",
    "web.blueprints.daily_candidates",
    "web.blueprints.video",
    "web.blueprints.discovery",
)


class AppIsolationTests(unittest.TestCase):
    def setUp(self):
        self.original_cwd = Path.cwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)
        self.env = patch.dict(os.environ, {"AWS_EC2_METADATA_DISABLED": "true"}, clear=True)
        self.env.start()
        self.cloud = patch("boto3.client", side_effect=AssertionError("Cloud access forbidden"))
        self.cloud.start()
        example = Path(__file__).resolve().parents[1] / "config" / "tenant.example.yaml"
        reset_tenant(load_tenant_from_path(example))
        reset_project_board()
        reset_tech_spend()
        reset_s3_store()

    def tearDown(self):
        reset_tenant()
        reset_project_board()
        reset_tech_spend()
        reset_s3_store()
        self.cloud.stop()
        self.env.stop()
        os.chdir(self.original_cwd)
        self.tmp.cleanup()

    def test_create_app_does_not_import_meme_pipeline(self):
        app = create_app(local_only=True)
        self.assertIsNotNone(app)
        for name in _MEME_PIPELINE_MODULES:
            self.assertNotIn(name, sys.modules)

    def test_example_tenant_home_has_no_iana_zone_and_memes_404s(self):
        example = Path(__file__).resolve().parents[1] / "config" / "tenant.example.yaml"
        reset_tenant(load_tenant_from_path(example))
        client = create_app(local_only=True).test_client()

        home = client.get("/")
        self.assertEqual(home.status_code, 200)
        html = home.get_data(as_text=True)
        self.assertIn("Waiting on you", html)
        self.assertIn("This week", html)
        self.assertIn("On the horizon", html)
        self.assertNotIn("America/New_York", html)
        self.assertNotRegex(html, r"(?:America|Europe|Asia|Pacific|Africa|Australia)/[A-Za-z_]+")
        self.assertIn('href="/projects/?project=home-ops#home-ops"', html)

        self.assertEqual(client.get("/projects/").status_code, 200)
        self.assertEqual(client.get("/spend/").status_code, 200)
        self.assertEqual(client.get("/x/").status_code, 404)
        self.assertEqual(client.get("/grok-bot/").status_code, 404)
        self.assertEqual(client.get("/memes/").status_code, 404)
        self.assertEqual(client.get("/healthz").status_code, 200)
