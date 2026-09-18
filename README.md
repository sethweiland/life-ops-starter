# Life Ops

An open-source personal dashboard you can make your own: projects, upcoming events,
decisions, recurring work, spending and optional weather. Customize it with your
coding agent or edit the Python, HTML and CSS yourself.

Anyone can use this starter. Each person creates an independent private
installation with their own configuration, accounts and data. There is no shared
hosted account to sign up for, and no access to anyone else's dashboard.

**[Start here →](docs/onboarding/start-here.md)** The basic local dashboard needs
Python 3.11+ and no cloud accounts, AWS setup or AI API keys.

This is an early release for people comfortable following setup instructions or
working with a coding agent. It is not a one-click hosted service. See
[what works today and what comes next](docs/roadmap.md).

Home brings together project decisions, calendar events and optional weather cues
for rain and what to wear. Optional pages show
spending, draft reviews, and recurring routines. Agents write records; you review
them. The dashboard does not launch agents, post messages, buy items, or cancel
services. See the [data contracts](docs/life-ops.md).

New to accounts, API keys or hosting? Start with the
[guided onboarding](docs/onboarding/start-here.md), then choose the connections you
need. It explains credential storage, verification and common setup failures.

| Start with | Guide |
| --- | --- |
| A useful dashboard without API keys | [First local session](docs/onboarding/start-here.md) |
| Your own design and layout with Codex | [Customization and copyable prompts](docs/customization.md) |
| Projects and common personal workflows | [The five primitives](docs/primitives.md) |
| Subscriptions, model usage and AWS costs | [Spend walkthrough](docs/onboarding/spend.md) |
| Umbrellas, layers and getting ready to go out | [Weather setup](docs/onboarding/weather.md) |
| Hosting with private access | [Login and credential rotation](docs/onboarding/authentication.md) |

Create an independent **private** copy before adding personal records. The starter
is source you can customize; it is not yet a packaged plugin framework. Style
changes are straightforward CSS/template work. A new provider connection still
needs code, scoped permissions and verification. See [known limitations](SECURITY.md).

## Run locally

Python 3.11 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --require-hashes -r requirements.txt
cp config/tenant.example.yaml config/tenant.yaml
python scripts/check_setup.py
python web/run.py --local
```

Open http://localhost:5050. Edit `config/tenant.yaml` to set your name, timezone,
projects, agents and navigation. The basic app needs no API keys or cloud account.
This explicit demo mode only accepts localhost requests and has no login.
Restart after changing configuration. Local runtime records are stored under
`data/` and must stay private.

Calendar, spending and routine records start empty. Example projects are fictional.
Optional modules are enabled in your configuration. The routine catalog retains
the `/grok-bot/` route and `grok_bot` config key for compatibility; it supports any
agent name. Enabling it does not install an agent or schedule a task.

To explicitly try fictional routine data, copy `examples/routines.json` to
`data/grok_bot_routines.json` and enable `modules.grok_bot`. These examples are never
loaded automatically. Do this only in a local demo, without a production bucket.

## Keep your installation private

- Keep personal configuration and extensions in a separate private repository.
- Keep runtime records and credentials outside the public source tree and history.
- This repo ignores local config, runtime data, deployment config and `.env` files.
  Review every commit: ignore rules do not remove already tracked files or history.
- Use fictional records in public tests, screenshots, issues, logs and examples.
- Each installation needs its own private storage. There is no shared hosted service.

Use [AGENTS.md](AGENTS.md) when customizing with Codex or another coding agent.

## Optional integrations and hosting

Copy `.env.example` to `.env` for optional environment settings. `CALENDAR_ICS_URL`
can supply a private calendar feed; never commit that URL. Without it, agents may
write `data/calendar/snapshot.json` using the documented contract.

For private S3 storage, configure `OPS_BUCKET` and AWS credentials in the environment.
The older `MEME_ASSETS_BUCKET` variable is also accepted. Objects live under `ops/`;
each installation should use its own private bucket. A deployed container requires
durable storage: local files in an ephemeral container are not a backup.

For Fly, copy `fly.example.toml` to `fly.toml` and replace the placeholder app name
with your own app. Setup must never reuse someone else's deployment or bucket.
Follow [hosted authentication setup](docs/onboarding/authentication.md) before
starting the hosted app. It requires a generated owner access key, a session
signing secret and one exact HTTPS origin. Missing settings prevent startup.
Other hostnames are rejected; requests for private records require login.
An external access gateway can provide another layer of protection.

Every browser edit requires a CSRF token, including in the local demo. Custom
clients must preserve the login session, send the page's `X-CSRFToken`, and use a
JSON object for API writes. Agents should continue writing the storage contracts
with their own narrowly scoped credentials rather than using the owner's login.

The example Fly config allows machines to sleep when idle. Keeping a machine awake
can reduce first-visit startup delays but adds running cost.

## Development and release preparation

```bash
python -m pip install --require-hashes -r requirements-dev.txt
python -m pytest
python scripts/export_public.py --output dist-public/life-ops
```

The exporter copies only the files in `scripts/public-files.txt`, rejects symlinks
and private paths, and produces a history-free directory and tar archive. Review
both before publishing; an allowlist is not a substitute for checking the contents.
Never publish the original repository history as part of a sanitized export.
The source is licensed under [MIT](LICENSE); dependencies and optional external
data retain their own [licenses and attribution](docs/attribution.md). See
[contributing](CONTRIBUTING.md), [security reporting](SECURITY.md) and the
[release checklist](docs/releasing.md).

Each worker caches calendar snapshots and crest maps for 30 seconds. Saves clear
that worker's snapshot cache; date grouping is recalculated on each visit. External
agent changes appear after the short cache expires.
