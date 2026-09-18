# Connect Spend, one source at a time

Spend is a planning view of supplied records. It does not log into your bank,
discover subscriptions, cancel services, read ChatGPT/Codex subscription invoices,
or automatically retrieve OpenAI, Anthropic or xAI billing. An AI account login is
not a billing integration. You can get useful results without any API key.

## Choose the source

| What you want | Supported source | Credentials held by the dashboard |
| --- | --- | --- |
| Subscriptions, domains, hosting, or other recurring expenses | Your JSON ledger | None for local files; storage identity for S3 |
| Usage from your own instrumented applications/agents | Monthly token-event files, by provider | Storage identity only; model API keys stay with the producing app |
| AWS account costs | Optional Cost Explorer API, explicitly enabled | AWS runtime identity with cost-read permission |
| Bank feeds, provider invoice sync, automatic subscription discovery | Not built in | Do not grant credentials for an unimplemented connector |

All values are USD. Annual subscriptions are divided by 12; recorded variable
amounts and usage are month to date, not a forecast. The combined planning total
mixes these bases deliberately and is labelled accordingly. It is not an invoice,
cash balance, full household budget, or proof that every cost is connected.

## 1. Get a manual ledger working

Start in a fresh local installation without a production bucket. Create `data/`
and copy `examples/tech-spend.json` to `data/tech_spend.json` only if no ledger
already exists. Open Spend. The fictional example should show:

- USD 10/month for notes, assigned to Writing.
- USD 60/year for a domain → USD 5/month, assigned to Shared.
- USD 3 in recorded hosting usage, assigned to Home Ops.
- Fixed total USD 15, variable total USD 3, planning total USD 18.

This is your first acceptance check. Replace the example with your real ledger
privately after verifying it. Don't merge fictional amounts into a real ledger.
Use stable service IDs, actual prices and your own project IDs:

```json
{
  "last_updated": "2026-09-01",
  "subscriptions": [
    {
      "id": "notes",
      "name": "My notes service",
      "category": "fixed",
      "amount_usd": 10,
      "cadence": "monthly",
      "status": "active",
      "project": "writing"
    }
  ],
  "cancelled": []
}
```

Use `monthly`, `yearly`, or `usage` cadence; `fixed` or `variable` category; and
`active` or `cancelling` for costs still paid. Keep cancelled history in `cancelled`.
Amounts must be finite, nonnegative USD values. This release does not model refunds
or currency conversion. Removing a row does not cancel the subscription.

For shared costs, use `"projects": {"writing": 0.6, "shared": 0.4}` instead of
`project`. A missing tag or unassigned share appears under Unallocated.
Update `last_updated` when reviewing the ledger so you can recognize stale inputs.
The dashboard does not infer a future charge or a free hosting trial from a vendor name.

## 2. Optional shared storage

The key is `ops/spend/tech_spend.json` in your private `OPS_BUCKET`. With a bucket
configured, S3 takes precedence over the local file. Editing the local fallback
will not replace a valid remote ledger. The Sources panel identifies the source.

Use the [S3 recipe](connections.md#a-private-s3-records) to establish a runtime
identity. Give a ledger producer write access only to this key, and the dashboard
read access. The dashboard's project and draft features need separate scoped
write permissions. Use a dedicated private bucket, block public access, and enable
versioning/backups according to your recovery needs. Verify a fictional ledger
round trip before granting access to real records.

**Disconnect:** back up the ledger, stop its producer, remove the bucket setting
or that identity's permissions, and confirm the intended local fallback. A fallback
may be older than the remote version; compare timestamps privately.

## 3. Optional application usage logs

Set the provider IDs whose records you actually produce:

```dotenv
LIFE_OPS_USAGE_PROVIDERS=openai,anthropic,xai
```

This selects files, not provider API connections. Each provider is a simple lowercase
ID. Leave the setting unset for the legacy xAI-only view, or empty to disable logs.
The local path is `data/usage/{provider}/{YYYY}/{MM}.json`; the S3 key is
`ops/usage/{provider}/{YYYY}/{MM}.json`.

Have the application that makes model calls record provider, model, timestamp,
input/output token counts, project and an explicit `estimated_cost_usd`. Use actual
usage returned by the provider and a reviewed pricing calculation or known cost;
never invent it from a chat transcript. The producer owns its API key. The dashboard
reads only the resulting records. The [full event contract](../life-ops.md) and
`src/core/token_tracker.py` include the schema and a writer.

A producer importing this source can use:

```python
from src.core.token_tracker import log_token_usage

# Fictional example only. Substitute verified response usage and cost in your app.
log_token_usage("openai", "example-model", 100, 50,
                estimated_cost_usd=0.01, project="writing")
```

Run the producer with its own correctly configured runtime environment. Calling
this Python function does not load your shell's missing `.env` or connect a model.
Never replay the same event as a new write: each call generates a new event ID.
For an external producer, preserve stable event IDs and use the documented merge
semantics rather than overwriting a monthly object with one new event.

Open Spend during the event's month; the current view does not select past months.
Verify provider/source, one call, 150 tokens, USD 0.01 and the Writing attribution
for the example. S3 is read before local records. The current view uses the server's
calendar month. Compare provider bills separately; counts and billed amounts can differ.

Non-xAI records without a price are marked incomplete; that provider's log is
excluded from cost totals and its saved ledger amount is retained. Explicit zero
is a valid known amount. Historical xAI records without explicit prices retain
the old `0.045 USD / million tokens` heuristic for compatibility; it is not current
provider pricing and should be replaced by explicit verified cost estimates.

Avoid counting the same cost twice. A complete provider log replaces an active
ledger row named `{provider}-tokens` (for example `openai-tokens`). Other IDs are
treated as independent costs. An unpriced or unavailable log does not replace that
row. A ChatGPT-style monthly subscription and separately billed API usage are
different costs—record them separately only when both apply to you.

**Disconnect:** stop the producer or remove its provider ID from the view. Revoke
unused producer credentials at the provider. Hiding usage does not stop model calls.

## 4. Optional AWS Cost Explorer

This is disabled even if AWS credentials already exist. It uses Boto3's credential
chain, so profiles, temporary sessions and workload roles work without requiring
a permanent key pair in environment variables. See [Boto3 credentials](https://docs.aws.amazon.com/boto3/latest/guide/credentials.html)
and AWS's [temporary identity and least-privilege guidance](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html).

1. Enable Cost Explorer for the intended account and verify its billing data in
   the console. Billing access and data availability are separate from S3 access.
2. Establish the runtime's AWS identity using [the credential guide](secrets.md).
   Confirm the account privately. A payer/management account may expose more than
   one account's costs; do not connect an identity whose scope you do not intend.
3. Grant `ce:GetCostAndUsage` only for the intended billing scope. Consult the
   current [AWS API permission guidance](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-api.html)
   and [Cost Explorer authorization reference](https://docs.aws.amazon.com/service-authorization/latest/reference/list_ce.html)
   for your billing-view/resource arrangement. Do not grant administrator access.
4. Review [current API pricing](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/pricing/).
   Requests can incur charges. Then set `LIFE_OPS_AWS_COSTS=true` and restart.
5. Open Spend once. Check the timestamp and date range, and compare the result to
   the console's UnblendedCost metric for the same range and account.

The endpoint is `ce.us-east-1.amazonaws.com`. The app queries month-to-date complete
days with an exclusive end date, caches success/failure for one hour per worker,
and bounds timeouts/retries. Restarts or additional workers can make extra calls.
The first day of a month has no complete days and makes no query. Billing data can
lag and is not a final invoice. Unsupported currencies are rejected rather than
labelled USD.

A successful reading replaces the saved `aws` ledger row. Its allocation comes from
that row; with no active row, the amount appears as Unallocated. On an error, the
saved amount remains in totals and a sanitized warning appears. Full provider
exception text is not displayed.

**Disconnect:** set `LIFE_OPS_AWS_COSTS=false`, restart every worker and revoke the
cost permission if unused. The manual `aws` amount becomes the source again.

## Verify before relying on the dashboard

Check one known value for each source, source timestamps, annual conversion,
project splits, incomplete logs, provider failures and duplicate IDs. A green
setup check validates format, not permissions or billing accuracy. Keep a private
record of source, identity, last verification and disconnection steps in your
[setup checklist](setup-checklist.example.md).
