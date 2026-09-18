"""Generate a single-owner login without printing secrets or contacting providers."""

import argparse
import hashlib
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.auth_config import normalize_origin


def generate_auth(origin: str, output: Path) -> None:
    origin = normalize_origin(origin)
    # Refuse existing directories, including symlinks: never replace working keys.
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    access_key = secrets.token_urlsafe(32)
    server_env = (
        f"LIFE_OPS_ORIGIN={origin}\n"
        f"LIFE_OPS_OWNER_KEY_SHA256={hashlib.sha256(access_key.encode()).hexdigest()}\n"
        f"LIFE_OPS_SESSION_SECRET={secrets.token_urlsafe(48)}\n"
    )
    for name, content in [("owner-access-key.txt", access_key + "\n"), ("server.env", server_env)]:
        fd = os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True, help="Your exact HTTPS site origin")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "instance/auth",
                        help="New private directory (default: instance/auth)")
    args = parser.parse_args(argv)
    try:
        generate_auth(args.origin, args.output_dir)
    except (OSError, ValueError):
        print("Setup failed. Use a valid HTTPS origin and a new writable private directory. Existing files are never overwritten.")
        return 1
    print("Created owner-access-key.txt and server.env in your private output directory.")
    print("Save the access key in your password manager. Import server.env into your host's secret settings.")
    print("Values are not printed. See docs/onboarding/authentication.md for setup and rotation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
