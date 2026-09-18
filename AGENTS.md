# Working on Life Ops

This repository is the reusable core. Public examples and tests must be fictional.
Personal configuration, workflows and extensions belong in an owner's private
installation. Records and secrets belong in private storage, outside source history.

## Development

- Read README.md for setup and docs/life-ops.md for data contracts.
- For a new installation, follow docs/onboarding/start-here.md: local success first,
  then one connection at a time. Never ask someone to paste secret values into chat.
- `scripts/check_setup.py` is offline and redacts values. A PASS is not proof of
  provider access; follow the corresponding connection's verification recipe.
- Use Python 3.11 or newer. Install requirements.txt in a virtual environment.
- Run `python -m pytest` after changing behavior.
- Install development tools from requirements-dev.txt with --require-hashes.
- For styling, see docs/customization.md; for Spend, use docs/onboarding/spend.md.
  Keep model keys in the record-producing application, and billing reads opt-in.
- Weather is optional and lazy-loaded on Home; follow docs/onboarding/weather.md.
  Never infer the owner's location or use real forecasts in tests.
- Hosted `create_app()` requires the generated login settings. `local_only=True`
  is for loopback demos and isolated tests; never add it to the hosted entry point.
- Preserve authentication and CSRF on every private route. Never ask for the
  owner's access key in chat; use docs/onboarding/authentication.md.
- Keep existing route and JSON contracts compatible unless a migration is explicit.
- Use configuration for agent names, timezones, domains, projects and navigation.
- The app displays agent work; it does not run agents or perform external actions.
- Disabled modules must not seed private stores. Demo data is explicitly opt-in.
- Tests must use temporary storage and synthetic records, never production accounts.

## Privacy and release preparation

- Never copy personal calendar entries, spending, routines, credentials, account
  identifiers, screenshots or private logs into public examples, commits or issues.
- Do not inspect or publish `.env`, private config or runtime records for a generic
  core change. A private-instance task may use only the records needed for that task.
- `scripts/public-files.txt` is the explicit release allowlist. Review additions.
- Build a history-free candidate with `scripts/export_public.py`; review its contents
  and attribution before publishing. Git history is not part of that export.
- Do not change repository visibility or a live deployment as a side effect of setup.

## Starter customization prompt

"Help me configure my own private Life Ops installation. Read README.md and the data
contracts. Set my preferred timezone, projects, agents and navigation in my private
configuration. Start with empty runtime records. Keep credentials in the environment,
use fictional records in tests, and verify the app locally before any deployment."
