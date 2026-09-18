"""The release artifact must not pick up local private files or Git history."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest

from scripts.export_public import export_public, public_files, ROOT


def test_export_copies_only_reviewed_files_and_scrubs_archive_metadata(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "README.md").write_text("Public example")
    (root / ".env").write_text("PRIVATE_SENTINEL")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("PRIVATE_SENTINEL")
    manifest = root / "manifest.txt"
    manifest.write_text("README.md\n")
    output = tmp_path / "public"
    archive = export_public(output, root, manifest)
    assert {p.name for p in output.iterdir()} == {"README.md", "PUBLIC_FILES.sha256.json"}
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            assert member.uid == member.gid == member.mtime == 0
            assert member.uname == member.gname == ""
            assert b"PRIVATE_SENTINEL" not in tar.extractfile(member).read()


@pytest.mark.parametrize("name", [".git/config", ".env", ".env.production", "data/routines.json",
                                  "config/tenant.yaml", "../outside", "/tmp/outside", "fly.toml"])
def test_private_paths_cannot_be_allowlisted(tmp_path, name):
    manifest = tmp_path / "manifest"
    manifest.write_text(name + "\n")
    with pytest.raises(ValueError):
        public_files(tmp_path, manifest)


def test_versioned_exports_keep_the_full_version_in_archive_names(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "README.md").write_text("Fictional starter")
    manifest = root / "manifest.txt"
    manifest.write_text("README.md\n")
    for version in ("0.1.0", "0.1.1"):
        archive = export_public(tmp_path / f"starter-v{version}", root, manifest)
        assert archive.name == f"starter-v{version}.tar.gz"
        assert archive.is_file()


def test_symlink_cannot_export_outside_content(tmp_path):
    secret = tmp_path / "secret"
    secret.write_text("PRIVATE_SENTINEL")
    (tmp_path / "example.txt").symlink_to(secret)
    manifest = tmp_path / "manifest"
    manifest.write_text("example.txt\n")
    with pytest.raises(ValueError, match="Symlinks"):
        public_files(tmp_path, manifest)


def test_real_export_boots_without_hidden_configuration_or_credentials(tmp_path):
    output = tmp_path / "public"
    export_public(output)
    # This is a separate interpreter with no inherited provider or tenant settings.
    program = '''
from unittest.mock import patch
from web import create_app
from src.core.grok_bot import get_grok_bot_routines
from src.core.tenant import load_tenant
with patch("boto3.client", side_effect=AssertionError("Unexpected cloud request")):
    try:
        create_app()
        raise AssertionError("Hosted app must refuse missing authentication")
    except ValueError:
        pass
    app = create_app(local_only=True)
    client = app.test_client()
    for path in ["/", "/projects/", "/spend/", "/healthz"]:
        assert client.get(path).status_code == 200, path
    assert client.get("/grok-bot/").status_code == 404
    assert load_tenant().human_name == "Your Name"
    assert get_grok_bot_routines().load() is None
'''
    result = subprocess.run([sys.executable, "-c", program], cwd=output,
                            env={"PATH": str(Path(sys.executable).parent), "AWS_EC2_METADATA_DISABLED": "true"},
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    manifest = json.loads((output / "PUBLIC_FILES.sha256.json").read_text())
    assert manifest["algorithm"] == "sha256"
    for entry in manifest["files"]:
        assert hashlib.sha256((output / entry["path"]).read_bytes()).hexdigest() == entry["digest"]
    files = [entry["path"] for entry in manifest["files"]]
    assert not any(name.startswith(("data/", ".git/", "output/")) for name in files)
    assert "config/tenant.yaml" not in files


def test_container_copies_source_explicitly():
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert "COPY . ." not in dockerfile
    assert "COPY config/tenant.example.yaml ./config/tenant.example.yaml" in dockerfile
    rules = (ROOT / ".dockerignore").read_text().splitlines()
    for path in ["data/grok_bot_routines.json", "output/", "private/", "instance/", ".env.*"]:
        assert path in rules
