# Contributing

Use fictional records, names, domains and screenshots in every public change.
Never copy a private installation's configuration, logs or account credentials.
Report vulnerabilities through [SECURITY.md](SECURITY.md).

```bash
python -m pip install --require-hashes -r requirements-dev.txt
python -m pytest
python -m bandit -r src web scripts -ll
python scripts/export_public.py --output dist-public/review
```

Keep a change focused. Explain the user-visible problem, new behavior, migration
requirements and validation. Add tests for meaningful behavior or security changes.
Every private route must retain authentication and every mutation must retain
CSRF protection. Keep provider calls opt-in; use mocks and temporary storage in tests.

The five primitives are [documented here](docs/primitives.md). Prefer adapting an
existing primitive before adding a new one. A new connector needs an onboarding
recipe describing its purpose, scopes, costs, secret handling, verification,
revocation and error behavior. Styling-only changes should not change data contracts.

Runtime dependencies are declared in requirements.in. Development tools are in
requirements-dev.in. The generated .txt files pin transitive versions and hashes:

```bash
pip-compile --generate-hashes --allow-unsafe --output-file requirements.txt requirements.in
pip-compile --generate-hashes --allow-unsafe --output-file requirements-dev.txt requirements-dev.in
python -m pip_audit --require-hashes -r requirements.txt
python -m pip_audit --require-hashes -r requirements-dev.txt
```

Review updates, run both Python versions in CI, and include all four dependency
files in the same PR when applicable. Never add an unexplained scanner exclusion.
Add new public files individually to scripts/public-files.txt, then inspect the
export before proposing publication.
