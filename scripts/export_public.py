"""Export a reviewed file allowlist without runtime data or Git history."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "scripts/public-files.txt"
PRIVATE_PARTS = {".git", ".venv", "__pycache__", "data", "private", "instance",
                 "output", "dist-public", "node_modules"}
PRIVATE_FILES = {"config/tenant.yaml", "fly.toml", "secrets.local.json"}


def public_files(root: Path = ROOT, manifest: Path = MANIFEST) -> list[Path]:
    files = []
    seen = set()
    for line in manifest.read_text().splitlines():
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        relative = PurePosixPath(name)
        if (relative.is_absolute() or ".." in relative.parts or "\\" in name
                or name in seen or PRIVATE_PARTS.intersection(relative.parts)
                or name in PRIVATE_FILES
                or any(part.startswith(".env") and part != ".env.example"
                       for part in relative.parts)):
            raise ValueError(f"Unsafe or duplicate public path: {name}")
        source = root / name
        if any(path.is_symlink() for path in [source, *source.parents]):
            raise ValueError(f"Symlinks cannot be exported: {name}")
        if not source.is_file() or not source.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Missing or outside public root: {name}")
        seen.add(name)
        files.append(Path(name))
    return files


def export_public(output: Path, root: Path = ROOT, manifest: Path = MANIFEST) -> Path:
    root = root.resolve()
    output = output.resolve()
    if output == root or root.is_relative_to(output):
        raise ValueError("Export destination must not contain the source repository")
    archive = output.with_name(output.name + ".tar.gz")
    if output.exists() or archive.exists():
        raise ValueError("Export destination already exists; choose a new directory")
    files = public_files(root, manifest)
    # Validate everything before creating an artifact; never overwrite a prior export.
    output.mkdir(parents=True)
    checksums = []
    for relative in files:
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, destination)
        checksums.append({"path": relative.as_posix(),
                          "digest": hashlib.sha256(destination.read_bytes()).hexdigest()})
    # Separate filenames from digests so secret scanners do not mistake a file
    # named auth/secrets/token for a credential assignment. No scan exclusions.
    (output / "PUBLIC_FILES.sha256.json").write_text(
        json.dumps({"algorithm": "sha256", "files": checksums}, indent=2) + "\n")
    with tarfile.open(archive, "w:gz") as tar:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                info = tar.gettarinfo(str(path), arcname=str(Path(output.name) / path.relative_to(output)))
                # Do not leak local usernames, group names, permissions, or timestamps.
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ""
                info.mode = 0o644
                with path.open("rb") as source:
                    tar.addfile(info, source)
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(export_public(args.output))


if __name__ == "__main__":
    main()
