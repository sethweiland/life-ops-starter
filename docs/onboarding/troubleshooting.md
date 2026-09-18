# Troubleshooting setup

Start with the exact step that failed. Run the offline checker with the same local
configuration and explicit `.env` file you intend to use. Never include values in
a support request.

```bash
python scripts/check_setup.py --config config/tenant.yaml --env-file .env
```

Omit `--env-file` if you have none. The checker reads no `.env` by default, does not
expand `${VARIABLE}` expressions, and never fetches a remote tenant or secret.
It validates settings, not provider connections or authentication on a hosted app.

| Symptom | Likely distinction | Next check |
| --- | --- | --- |
| `python` or `pip` not found | Python vs virtual environment setup | Use the correct platform commands in Start here; try the virtual environment's Python directly |
| Import/module error | Packages installed in another environment | Activate `.venv`; use `python -m pip install -r requirements.txt` |
| Port already in use | Another local process is listening | Use another `WEB_PORT` in the environment; do not stop unknown processes |
| Personalization doesn't change | Startup-cached tenant or wrong config source | Restart; check `TENANT_CONFIG`, then S3 tenant, then local tenant, then example fallback |
| An existing project retains its old status | Runtime board and seed config are different | Update the persisted project through the UI/contract; do not erase the real board to reset a demo |
| Page returns 404 | Module disabled | Check its boolean flag in the effective tenant config |
| `NoCredentialsError` | Runtime has no AWS identity | Verify its profile/session/role; website login alone is insufficient |
| Expired AWS session | Identity existed but expired | Renew that profile/session and retry; don't create a second permanent key |
| `AccessDenied` | Identity exists but lacks required permissions | Verify account, resource and operation; inspect scoped IAM/KMS policy |
| S3 works, live AWS spend doesn't | Separate opt-in and billing permission | Check LIFE_OPS_AWS_COSTS, identity and ce:GetCostAndUsage scope in the Spend guide |
| App works despite a wrong secret ARN | Silent environment fallback | Verify Secrets Manager retrieval independently without printing values |
| Rotated AWS secret still uses old value | Process-lifetime helper cache | Restart the app after rotation and verify the intended operation |
| `secrets.backend: aws` fails | Adapter name is reserved, not implemented | Use `env`; read the limited `APP_SECRET_ARN` recipe before choosing AWS retrieval |
| Feed configured but calendar empty | Wrong feed format, no matching dates, auth failure or parser limitation | Verify a known upcoming event; check provider feed permissions and supported format privately |
| Calendar appears unchanged | Snapshot/ICS caching | Allow refresh time and confirm the producing agent/feed actually changed |
| Records vanish after deploy | Ephemeral local container storage | Restore from backup and configure durable storage before adding real records |
| Startup reports a LIFE_OPS setting error | Hosted login settings missing or invalid | Follow Authentication setup; run the checker with `--hosted` and your private env file |
| Hosted app returns 403 | Wrong hostname, HTTP, or proxy configuration | Check exact LIFE_OPS_ORIGIN, HTTPS, and the trusted proxy hop setting |
| An edit says the page expired or cannot be verified | CSRF token expired, missing, or referrer stripped | Reload; keep session cookies enabled; ensure the proxy preserves the same-origin referrer policy |
| Signed-out visitors can see private records | Local demo was exposed or the deployed version lacks the new boundary | Restrict exposure; deploy the hosted entry point and verify all hostnames |

## A useful support request

Include the setup step, operating system, Python version, whether this is local or
hosted, enabled capability, sanitized error code, and what you expected. The checker
prints fixed messages rather than credential values, but still review what you share.

Exclude `.env`, credential values, private feed URLs, tenant files, actual calendar
records, spending records and unreviewed logs. A provider error can include account
IDs, secret identifiers or URLs even when it omits the secret value itself.

## When the guide is incomplete

If a provider or manager isn't listed as supported, stop and identify the missing
adapter before creating accounts or paying for services. Record the gap as a feature
request with a fictional example. Documentation should not disguise unfinished
integration work as a configuration task.
