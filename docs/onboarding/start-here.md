# Start here

Get a useful local dashboard before connecting any accounts. Then add only the
capabilities you want, one at a time. You can stop at any stage and keep using it.

## Choose your first goal

| Goal | What you need | What you can skip |
| --- | --- | --- |
| Track projects and decisions on this computer | Python 3.11+, source code | Cloud hosting, AWS, AI API keys |
| Show your calendar | A private ICS feed, or an agent that writes a snapshot | A new AI account; built-in Google OAuth is not available |
| Know whether to bring an umbrella or a jacket | Approximate city coordinates; optional weather module | Weather API keys, GPS tracking |
| Share records between your own agents and the dashboard | Private S3 bucket and AWS identity | Secrets Manager unless you choose it |
| Open the dashboard from another device | Hosting, durable storage and an authentication layer | A custom domain initially, if all ingress is protected |
| Review drafts or see routines | An existing agent producing the documented JSON | Giving the dashboard the agent's model or social-account keys |

Having a coding assistant does not automatically connect its accounts to the app.
Connections belong to whichever process actually calls that service. See the
[connection map](connections.md) before creating keys.

## 1. Start locally

Clone or download the starter and open its folder in your editor. Use an
independent private copy before adding personal records; see
[Customization](../customization.md). A coding agent can follow the prompts there.
In a terminal at that folder, check `python3 --version`. If Python is missing, use the current
installer for your operating system from [python.org](https://www.python.org/downloads/).

On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --require-hashes -r requirements.txt
cp config/tenant.example.yaml config/tenant.yaml
python scripts/check_setup.py
python web/run.py --local
```

On Windows PowerShell, use `py -3` for the first command, then
`.venv\Scripts\Activate.ps1` to activate the environment and
`Copy-Item config/tenant.example.yaml config/tenant.yaml` to copy configuration.
If activation is restricted, use `.venv\Scripts\python.exe` directly with
`-m pip` and the script paths instead of changing system security settings.

Open http://localhost:5050. Home and Projects should load. An empty calendar and
empty spending page are normal. This is a local development server, not a hosting
setup. No cloud account should be needed for this first success.

**Checkpoint:** you can load Projects and change one example project's status.

## 2. Make it yours

Edit `config/tenant.yaml`:

- `human.name` and `human.timezone`: your display name and an IANA timezone.
- `projects`: your projects; leave unknown progress fields blank.
- `agents`: display names of the agents you already use.
- `modules` and `folders`: choose which pages and navigation entries appear.

Restart the server after configuration changes. Enabling a module only exposes
its page; it does not authorize accounts or install the external agent.

Keep this file private. Existing project records persist in `data/projects/board.json`:
editing the example YAML is not a reset button. Use a fresh demo folder if you want
to experiment with a blank installation, rather than deleting real records.

**Checkpoint:** the project list and timezone match your choices after restart.

## 3. Choose where credentials live

Read [Credentials and secret storage](secrets.md). For a local trial, a private
`.env` file is supported. Hosted environment secrets are also supported. AWS
Secrets Manager is optional and has specific limitations in the current core.

Copy `.env.example` to `.env` only when needed. Fill it in locally; don't paste live
credentials into a public issue, documentation, screenshots or a setup prompt.

```bash
python scripts/check_setup.py --config config/tenant.yaml --env-file .env
```

The checker inspects local settings without contacting a provider or printing
values. `PASS` means a local check passed; `CHECK` means a separate verification is
needed; `FAIL` means fix that item before proceeding. Exit code 1 means a failure.
It does not fetch S3 configuration or verify that any account is connected.

## 4. Connect one capability

Use [Connections](connections.md). Each recipe identifies who owns the credential,
what access is required, where to configure it, what success looks like and how to
disconnect. Record progress in a private copy of the
[setup checklist](setup-checklist.example.md).

A connection is finished only when you have verified the intended result. A green
local settings check or the presence of an API key alone is not enough.

For Spend, follow [the dedicated walkthrough](spend.md): the first checkpoint is
a fictional USD 18 ledger, before any billing APIs or usage producers are connected.
For practical forecast cues on Home, follow [Weather setup](weather.md).

**Checkpoint:** one known event, test project update, or test draft reaches the page
you expected. Then add the next connection.

## 5. Host it when the local version works

Choose hosting and a durable private storage location. Keep local and production
configuration separate. Complete [hosted authentication setup](authentication.md)
before starting the internet-facing app. The default WSGI entry point refuses
missing login settings. The `--local` demo is restricted to this computer and
must not be forwarded through a tunnel or reverse proxy.
Check both the configured domain and the provider's default hostname while signed out.

Copy `fly.example.toml` to `fly.toml` only if using Fly, and choose your own app name.
Use the provider's secret controls rather than putting values in deployment files.
See [Fly's secret documentation](https://fly.io/docs/apps/secrets/) for how its
environment secrets are supplied to running machines.

Verify a redeploy preserves your test records, then make and restore a test backup
in an isolated location. Record the procedure privately. A working web page does
not establish that storage persists or that access is protected.

## Ask your coding agent to guide you

Copy this prompt into a task opened on your own private installation:

> Read the onboarding guide. Help me get the local dashboard working first. Ask
> which capability I want next and which relevant accounts I already have. Explain
> the purpose of each credential and the smallest access it needs. Guide me through
> entering secrets locally without asking me to paste them into this conversation.
> Verify one connection at a time, record only non-secret progress in my private
> checklist, and stop before any public deployment until access and storage checks
> are ready. Distinguish supported integrations from features we would need to build.

If something fails, use [Troubleshooting](troubleshooting.md). Keep provider error
codes and the failed step; avoid copying full logs that might contain private URLs.
