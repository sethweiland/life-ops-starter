# Connect one capability at a time

The dashboard reads records. A separate agent may need access to the service that
produces those records. Give credentials to the process making the request.

| Connection | Status | Credential belongs to | Required for basic dashboard? |
| --- | --- | --- | --- |
| Local projects and ledger | Supported | No external credential | Yes, local files only |
| Private S3 records | Supported, optional | Dashboard and authorized record-writing agents | No |
| Calendar ICS feed | Supported, optional | Dashboard runtime | No |
| Calendar JSON snapshot | Supported, optional | Writing agent owns upstream calendar credentials | No |
| [Weather and clothing cues](weather.md) | Supported, explicit opt-in | No key; dashboard sends approximate coordinates to Open-Meteo | No |
| X drafts and routine catalog | JSON contracts supported | External agent owns model/social/scheduler access | No |
| Automatic account connection wizard | Planned | Not available yet | No |
| Gmail, bank, shopping, music or other provider OAuth | No built-in connectors in this core | Your chosen private integration | No |
| Live AWS Cost Explorer widget | Supported, explicit opt-in | Dashboard AWS runtime | No |

## A. Private S3 records

**Use it when:** the dashboard and your agents run on different machines, or your
host needs durable storage. Skip it for a local trial.

**Accounts and access:** create/use your own AWS account and a dedicated private
bucket. Keep public access blocked. Establish an AWS identity for each runtime;
the [secret-storage guide](secrets.md) explains profiles, roles and environment
settings. Scope its policy to this bucket and the records it needs.

The current dashboard reads objects, lists usage objects and writes project state,
optional calendar refreshes and catalog seeds under `ops/`. A starting permission
review therefore includes `s3:GetObject` and `s3:PutObject` on the appropriate
`ops/*` objects, and `s3:ListBucket` scoped to the relevant prefix. Additional KMS
permissions may apply if your bucket uses a customer-managed key. Tailor access to
enabled modules and review policies before applying them; do not grant an entire
account's storage access for this dashboard.

**Configure:** set `OPS_BUCKET` and `AWS_DEFAULT_REGION`, plus your chosen AWS
credential/profile mechanism. `MEME_ASSETS_BUCKET` remains a compatibility alias.
Put your private tenant config at `ops/tenant.yaml` if the deployed app loads it
from S3; do not upload credentials inside that file.

**Verify in a dedicated test instance:**

1. Confirm the runtime identity is the account/role you intended.
2. Write and retrieve one fictional test project through the intended storage path.
   Confirm the S3 object actually changed; local fallback can otherwise hide failures.
3. Restart the test app and confirm the same project state returns.
4. Have a test agent update that record and confirm the dashboard sees the change.
5. Record the bucket label and verification date privately, without object contents.

**If it fails:** missing credentials, wrong region, denied permissions and an expired
session are separate causes. A page showing local data does not prove S3 works.
See [Troubleshooting](troubleshooting.md).

**Disconnect:** back up the records you need, remove the bucket setting from every
source, and restart. The app then uses its local fallback, which may be empty or
older. This is not an automatic data migration. Revoke unused access separately.

## B. Calendar

Choose one path first:

- **ICS feed:** use a private feed URL offered by your calendar provider and set
  `CALENDAR_ICS_URL` in the dashboard environment. This URL can grant calendar access;
  treat it as a credential. A public share link or ordinary calendar webpage is not
  necessarily an ICS feed. Follow the provider's current export/subscription guide.
- **Snapshot:** let an existing private agent read your calendar and write the
  [snapshot contract](../life-ops.md#refresh-the-calendar-snapshot). Its calendar
  OAuth credentials belong to that agent. The dashboard receives only the snapshot.

Set `human.timezone` and enable the calendar module. The core provides no in-app
Google login or calendar-editing action. ICS support is a parser for supported
VEVENT fields; validate recurring, all-day and timezone-sensitive events with your
provider rather than assuming complete calendar synchronization.

**Verify:** choose one known upcoming event and check its title, local time and date
on Home. Compare an all-day or recurring event too if you use them. The calendar
reads are cached briefly and ICS refreshes use a longer cache; an immediate refresh
does not necessarily fetch upstream again.

**Disconnect:** remove the feed setting or stop the snapshot writer, and revoke the
feed/agent permission at the provider if appropriate. Previously cached snapshots
remain until you deliberately remove or replace them in your private storage.

## C. Agents, review drafts and routines

An agent runtime must already exist. Choose the agent you use and configure its
own model/provider credentials there. No model key is needed by the core merely
to display work that the agent has already done.

1. Add the agent's display name to `agents` in your private tenant configuration.
2. Give it access to only the private record locations it needs.
3. Point it at the [agent contract](../life-ops.md#agent-contract).
4. Have it write one fictional test item with a stable ID and a timestamp.
5. Verify that item appears in the intended project, draft queue or routine page.

Enable `modules.x` to review X-shaped draft records, or `modules.grok_bot` for the
routine catalog at `/grok-bot/`. These settings do not log in to X, create a cron
job, connect Grok, or publish a draft. Approval is recorded for your separate agent
workflow; decide explicitly how that agent treats approval before using real drafts.

**Disconnect:** stop the producer and revoke its storage access. Hiding the page
does not stop an agent or delete its previous records.

## D. Spending

Start with your own ledger in `data/tech_spend.json` or its S3 equivalent. No bank or
card login is required. The app displays supplied subscriptions and usage records;
it is not a bank aggregator. Token estimates are not authoritative invoices.

Follow [the complete Spend walkthrough](spend.md) for a known-total demo, ledger
fields, optional usage producers and Cost Explorer permissions. AWS reads are
explicitly opt-in and use the normal Boto3 credential chain, including profiles
and roles. The dashboard does not need model provider API keys to read usage logs.

**Verify:** enter a fictional ledger line with a known amount and project allocation,
then check the displayed total. Verify actual billing against the provider directly.
Removing a line from this dashboard never cancels a provider subscription.

## Adding another provider later

For every new integration, document: purpose, data read/written, responsible
process, account prerequisites, permission scopes, setup steps, secret location,
proof of connection, ongoing cost, expiration/rotation, and disconnection.

Do not describe a connection as built in until it exists and has a repeatable setup
test. Provider-specific OAuth flows and screenshot walkthroughs should be added
alongside each connector, using fictional accounts and current official references.
