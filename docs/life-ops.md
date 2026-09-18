# Life Ops

A human-gated life-ops shell. One human. Many agents. Self-hosted.

This document describes the configurable Flask core. Each owner supplies their
own private configuration and records. Domain-specific pipelines can run as
separate private services; they are not imported by this core.

Hosted requests require the owner's login; see
[authentication setup](onboarding/authentication.md). Browser write endpoints use
session-bound CSRF protection and require JSON objects. The explicit localhost
demo keeps CSRF protection but does not require a login. Authentication applies
to the whole instance; tenant configuration is not multi-user authorization.

---

## What it is

Agents write work. The human decides. Spend and routines attribute to
projects.

Home is an inbox of decisions, not a chatbot log and not a project-management
suite. It is Waiting on you first, then — when the calendar module is on —
This week and On the horizon from a snapshot or optional ICS feed. Never
invented events. Horizon starts the Monday after this week's Sunday, not
14 days out. The app never posts, buys, or cancels. There are no hub cards.

Optional weather adds **Before you head out** between the waiting inbox and calendar.
It is a read-only forecast view, not a new primitive. Enable `modules.weather` and
set approximate location/units in the private environment; see
[Weather setup](onboarding/weather.md). `/api/weather` requires the usual owner
session and returns an escaped HTML summary. Home loads it separately, so provider
latency does not block the dashboard. Disabled weather makes no provider requests.

## What it is not

- Not Linear
- Not Notion
- Not a meme app (memes are an optional module)
- Not a chatbot transcript
- Not a hosted SaaS

Domain UIs (memes, X, shopping, calendar) are optional modules. They must
not own the shell. The shell owns navigation, Home, Projects, and the
five primitives below.

Top nav is always **Home · Projects · Spend · X · Folders ▾**. X stays a
peer tab (human-gate inbox). Grok Bot and Memes tools nest under Folders
from tenant `folders:` — navigation config, not a sixth primitive.

---

## Five primitives

These describe the current core. Prefer reusing them when a workflow fits, and
introduce a new record type in an optional module when it has a distinct purpose.
See the [roadmap](roadmap.md). Tenant `folders:` are navigation bookmarks rather
than stored work objects.

### 1. Project

A named bet. One row on `/projects/`. Not a spend bucket with a different label.

| Field | Type | Notes |
|---|---|---|
| `id` | kebab-case string | Stable. Used by spend, queues, and routines. |
| `name` | string | Human label |
| `lane` | enum | Attention, not agile. See lanes below. |
| `owner_agent` | string or null | Who is supposed to move this (Grok Bot, Codex, Research Agent, …) |
| `updated_at` | ISO-8601 | Last write (human or agent) |
| `links.repo` | URL or null | |
| `links.prod` | URL or null | |
| `summary` | string or null | One-liner. Do not invent. |
| `last_done` | string or null | Agent-written. Empty if unknown. |
| `next_steps` | string or null | Agent-written. Empty if unknown. |

**Lanes** (attention, not sprint state):

| id | Product copy |
|---|---|
| `idea` | Idea |
| `active` | Active |
| `blocked` | Blocked |
| `waiting_on_you` | Waiting on you |
| `parked` | Parked |

Product copy and templates use `waiting_on_you`. Never hardcode
`waiting_on_owner`. On read, the alias `waiting_on_owner` normalizes to
`waiting_on_you` so old files do not break.

`shared` and `unallocated` are **Spend-only**. They are never project rows.

### 2. Queue item

One reviewable, agent-written thing.

| Field | Notes |
|---|---|
| `kind` | Module-specific (X: `follow` / `post` / `reply`; memes: daily candidate; …) |
| `payload` | The thing to review |
| `status` | `pending` \| `approved` \| `skipped` \| `done` |
| `project` | **Required.** Stamp a project id. |

X drafts (`ops/queue/x-activity/`) and meme daily candidates
(`ops/queue/daily-candidates/`) are modules of this shape. This release
does not rewrite those modules. New reviewable work should use the same
envelope rather than inventing a sixth primitive.

### 3. Human gate

Home (`/`) is the inbox of decisions.

The app **never**:

- posts to X
- publishes to Instagram on its own
- buys anything
- cancels a subscription
- starts or stops a Grok Bot routine

Approve / skip / move-lane are the verbs. Execution stays with the human
or with an agent the human already runs.

### 4. Cost event

Tokens and subscriptions stamp a project id.

- Token events: `ops/usage/{provider}/{YYYY}/{MM}.json` (`project` on each event)
- Subscriptions: S3 `ops/spend/tech_spend.json` when `OPS_BUCKET` is
  set, else local `data/tech_spend.json` (gitignored), else empty
  `{subscriptions: []}`. `project` or `projects` shares. Do not invent rows.

Leftovers stay visible as `shared` (overhead that is not one product) and
`unallocated` (missing tag). Spend never hides unlabeled dollars to clean
up a chart.

Project ids for Spend come from tenant config (project rows) plus the
two Spend-only ids. Do not keep a second hardcoded product list in Python
when the tenant file already has the ids.

`/spend/` shows this month's calls, tokens and logged cost estimates for the
configured usage providers, then the ledger. AWS Cost Explorer is separately
opt-in. Complete, priced logs replace the corresponding provider ledger row;
incomplete logs retain its saved amount. These are planning estimates, not
provider invoices. See [Connect Spend](onboarding/spend.md) for source selection,
verification, fallback behavior and the legacy xAI pricing heuristic. Unallocated means
“Missing project tag — shown on purpose.” Shared is overhead that is not one
product.

### 5. Routine

A scheduled job with an owner and a last run. The catalog already exists
at `ops/grok-bot/routines.json` (private local fallback: `data/grok_bot_routines.json`; fictional opt-in examples: `examples/routines.json`).

Routines attach to the shell via:

- `owner_agent` — already on each catalog row
- `project_id` (or `project`) — optional; accepted by the normalizer, not
  required on existing rows

This release documents the attachment. It does not start, stop, or invent
routine rows.

---

## Tenant config

Projects belong in config, not code.

| Path | Who |
|---|---|
| `config/tenant.example.yaml` | Starter configuration. Committed. Placeholder name. 2–3 example projects. 1–2 example folders. Modules off except `projects` + `spend` + `calendar` (empty snapshot is fine). No meme / X / Grok Bot links. `secrets.backend: env`. |
| `config/tenant.yaml` | Operator-private. **Gitignored.** Copy the example and put your bets in. Never commit this file. |
| `s3://$OPS_BUCKET/ops/tenant.yaml` | What Fly / Helper Agent use after the local file is gone from git. Same YAML shape. No secrets. |
| `tests/fixtures/` | Example tenants and spend ledgers for tests only. |

Each owner configures their instance from the five primitives plus the
example files. Operator-private life data does not live in git.

**Load order** (new installations have usable local defaults):

1. `TENANT_CONFIG` if set
2. S3 `ops/tenant.yaml` when `OPS_BUCKET` is set
3. `config/tenant.yaml` if present on disk
4. `config/tenant.example.yaml`

Relative `TENANT_CONFIG` paths resolve from the process cwd, then the repo root.
Helper Agent / operators upload their tenant to `ops/tenant.yaml`. Do not put secrets
in the YAML. This is not a multi-tenant SaaS — one human, one file.

### Reference

```yaml
human:
  name: Your Name          # display only
  timezone: America/New_York
  handle: ""               # optional public handle

site:
  title: Ops
  domain: ops.example.com  # footer / docs; not a bind address

modules:
  projects: true
  spend: true
  x: false
  grok_bot: false
  memes: false
  calendar: true
  weather: false          # Optional Home forecast and clothing cues; location stays private.

calendar:
  enabled: true            # Home This week / Horizon. No Google OAuth.

secrets:
  backend: env             # env | aws | bitwarden
  # Never put credentials in this file.
  # aws / bitwarden are documented backends; only `env` is implemented.

agents:                    # the humans-you-already-have, as ids
  - id: grok-bot
    name: Grok Bot
  - id: codex
    name: Codex

defaults:
  usage_project: home-ops  # stamped on token events when USAGE_PROJECT is unset

folders:                   # Folders menu. Nav only — not a sixth primitive.
  - id: life
    name: Life
    project_ids: [home-ops]
    links:                 # optional extra bookmarks
      - label: Home
        href: /            # or named route: route: home.index
  - id: work
    name: Work
    project_ids: [side-project]

projects:                  # named bets (list rows). Not shared / unallocated.
  - id: home-ops
    name: Home Ops
    lane: active
    owner_agent: grok-bot
    color: "#2563eb"       # optional; Spend pie
    description: ""        # optional; Spend subtitle
    links:
      repo: https://github.com/you/your-fork
      prod: ""
    summary: Personal life-ops shell
    last_done: null
    next_steps: null
```

Rules:

- `id` must match `^[a-z0-9]+(?:-[a-z0-9]+)*$` (projects and folders)
- `lane` must be one of the five lanes (or the `waiting_on_owner` alias)
- `shared` and `unallocated` in `projects:` are ignored (Spend-only)
- Folder `project_ids` that are not in `projects:` are skipped. Projects
  with no folder still appear on `/projects/`; they just do not show in Folders.
- Extra `links` may use `href` or a Flask `route`. If the href/route belongs
  to a disabled module, the link is omitted so the menu never 404s.
- A project with a module homepage (`memes` → `/memes/`, `x` → `/x/`) links
  there when that module is on; otherwise it deep-links to `/projects/#<id>`
  (and `?project=<id>`). `/projects/` rows use `id="project-<id>"`.
- No API keys, tokens, passwords, or ARNs in the YAML

---

## S3 / private key layout

The legacy `MEME_ASSETS_BUCKET` environment variable remains a compatibility alias
for `OPS_BUCKET`; the latter takes precedence.

All application S3 writes go through `S3Store` + `BucketLayout`
(`src/core/s3_store.py`). Public GET is only `public/memes/*`.

```
s3://$OPS_BUCKET/
├── public/memes/                         # PUBLIC (Instagram JPEGs + templates)
│   ├── templates/{id}.{ext}
│   └── generated/{hash}_{stem}.jpg
└── ops/                                  # PRIVATE
    ├── tenant.yaml                       # operator tenant (Helper Agent uploads this)
    ├── projects/board.json               # project list
    ├── calendar/snapshot.json            # read-only Home calendar
    ├── calendar/team-logos.json          # optional Home crests + category colors
    ├── spend/tech_spend.json             # operator spend ledger (not in git)
    ├── queue/daily-candidates/{YYYY-MM-DD}.json
    ├── queue/x-activity/{YYYY-MM-DD}.json
    ├── grok-bot/routines.json
    └── usage/{provider}/{YYYY}/{MM}.json
```

| Key | Local fallback when `OPS_BUCKET` is unset |
|---|---|
| `ops/tenant.yaml` | `config/tenant.yaml` or `config/tenant.example.yaml` |
| `ops/spend/tech_spend.json` | `data/tech_spend.json` (gitignored). Empty `{subscriptions: []}` if both missing. |
| `ops/projects/board.json` | `data/projects/board.json` |
| `ops/calendar/snapshot.json` | `data/calendar/snapshot.json` |
| `ops/calendar/team-logos.json` | `data/calendar/team-logos.json`. Empty `{match: [], teams: []}` if both missing. Optional chrome only. `match[]` stays backward-compatible for followed-team needles (Northbridge/Harbor). `teams[]` holds any team id with `aliases` + `logo_url` (longest alias wins). `title_parse.separators` and `categories[]` (hex + `google_color_id`) live on the same object. |
| `ops/queue/x-activity/{date}.json` | `data/x_activity/{date}.json` |
| `ops/queue/daily-candidates/{date}.json` | `data/daily_candidates/` |
| `ops/grok-bot/routines.json` | `data/grok_bot_routines.json` |
| `ops/usage/{provider}/{YYYY}/{MM}.json` | `data/usage/{provider}/{YYYY}/{MM}.json` |

If `ops/projects/board.json` (and the local file) are missing, the app
seeds the board from `tenant.yaml` `projects:` and writes through once.
Later tenant ids that are not yet on the board are merged in; existing
lanes / `last_done` / `next_steps` are not overwritten.

Never write ops JSON under `public/`.

---

## Module enable flags

| Flag | Routes | This release |
|---|---|---|
| `projects` | `/projects/` | Compact list (status pill = lane). Clipped summary / last done / next expand in place. Enabled in the starter configuration. |
| `spend` | `/spend/` | Ledger plus a Tokens widget at the top. Project ids from tenant. |
| `x` | `/x/` | Existing Research Agent draft review. Stays a top-level tab (human-gate inbox). |
| `grok_bot` | `/grok-bot/` | Existing routine catalog. Nested under Folders → Agents, not a peer tab. |
| `memes` | `/memes/` (404 here) | Flag only. Hides/no-ops folder links when off. The pipeline stays in a separate private application. |
| `calendar` | Home widgets only | This week + On the horizon (Monday after this Sunday through ~3 months). Snapshot or optional `CALENDAR_ICS_URL`. Optional crests from `ops/calendar/team-logos.json`: parse both sides of vs/@/against/v/— and show a logo when that team is in `match[]` or `teams[]`. Missing opponent logo = one crest. Soft category color (left border) from `categories[]` / heuristics / Google color id. No in-app Google OAuth. Not a sixth primitive. |

Disabled modules are hidden from the top nav and from Folders (module links
only). Their URLs still 404. The Folders menu itself never 404s. Home is
always on. Empty folders after filtering are omitted.

An owner who only wants a board and a spend page leaves `x`, `grok_bot`,
and `memes` false. They can leave `calendar` on with an empty snapshot.
They do not need Imgflip, Instagram, X, or Google credentials. Their
example folders have no meme / X / Grok Bot links.

---

## Secrets adapter

No secrets in git. No secrets in tenant YAML.

```
SecretsBackend.get(name, default="") -> str
```

| `secrets.backend` | Status |
|---|---|
| `env` | Implemented. Reads `os.environ` (and therefore `.env` / Fly secrets). |
| `aws` | Documented. Future: AWS Secrets Manager (the existing `src/core/secrets.py` helper already used by S3/memes is the likely backend). |
| `bitwarden` | Documented. Future: Bitwarden Secrets Manager. |

Tenant YAML may name the backend and, later, a secret *container* id
(ARN, collection). It must never contain the credential value.

Runtime today: set `TENANT_CONFIG` if you want a non-default file, or
upload `ops/tenant.yaml` to the bucket. Then put keys in the environment:

```
XAI_API_KEY=...
OPS_BUCKET=...          # optional; board falls back to data/projects/
CALENDAR_ICS_URL=...            # optional secret ICS; never put this in YAML
AWS_DEFAULT_REGION=us-east-1
```

See `.env.example`. AWS / Bitwarden backends are documented names only.

---

## Agent contract

Agents you already run (Grok Bot, Codex, Cursor, …) write the published
JSON. The Flask app does not spawn them.

### Update a project card

1. Read `ops/projects/board.json` (or `data/projects/board.json` locally).
2. Canonical shape: `{ "updated_at": ISO-8601, "projects": [ card, ... ] }`.
   A bare array is accepted **on read** as `projects` and is never written
   back as an array.
3. Find the card by `id`. Update only what you know:

   ```json
   {
     "id": "memes",
     "name": "Memes",
     "lane": "waiting_on_you",
     "owner_agent": "codex",
     "updated_at": "2026-09-11T22:00:00+00:00",
     "links": { "repo": "https://github.com/you/memes", "prod": null },
     "summary": "Example media meme pipeline",
     "last_done": "Shipped the project list",
     "next_steps": "Human: confirm status"
   }
   ```

4. Set `updated_at` on the card **and** the document.
5. Write the full object back to the same key. Do not put it under
   `public/`.
6. Do not invent `last_done` / `next_steps`. Leave them `null` if unknown.
7. Do not add `shared` or `unallocated` cards.
8. Lane moves from the human UI are `POST /projects/api/projects/<id>/lane`
   with `{ "lane": "active" }` (same-origin JSON, same pattern as `/x/`).
   Agents may write the file directly; they should not start routines or
   post to X from this contract.

Python helper (same process): `ProjectBoard.update_card(...)` /
`ProjectBoard.move_lane(...)`.

### Refresh the calendar snapshot

This is a read-only module, not a sixth primitive. Helper Agent / another agent
writes the snapshot. Flask does not talk to Google.

1. Read `ops/calendar/snapshot.json` (or `data/calendar/snapshot.json`).
2. Canonical shape:

   ```json
   {
     "updated_at": "2026-09-12T12:00:00+00:00",
     "timezone": "America/New_York",
     "events": [
       {
         "id": "dentist",
         "title": "Dentist",
         "start": "2026-09-12T14:00:00-04:00",
         "end": "2026-09-12T14:45:00-04:00",
         "all_day": false,
         "location": null,
         "url": null
       }
     ]
   }
   ```

3. Do not invent events. Leave `events` empty if you do not know them.
4. Never write calendar credentials into `tenant.yaml`. Owners who share a
   secret ICS set `CALENDAR_ICS_URL` in the environment; the app fetches,
   parses, and caches that feed into the same snapshot shape.
5. Home shows two lists only: **This week** (now through Sunday in the configured timezone) and
   **On the horizon** (Monday after this Sunday through ~3 months). Other
   events stay in the snapshot and are not shown.
6. Optional crests + category colors: `ops/calendar/team-logos.json` (or the
   local fallback) is the map your agent maintains in S3. Do not scrape ESPN or
   invent fixtures / logo URLs. A missing map or unmatched title leaves the
   row without a crest. IANA zone ids are still not printed.

   Shape (keep this; do not invent a different schema):

   ```json
   {
     "match": [
       {"id": "northbridge", "match_title_contains": ["Northbridge"], "logo_url": "https://…"}
     ],
     "teams": [
       {"id": "eastfield", "aliases": ["Eastfield", "Eastfield Boilermakers"], "logo_url": "https://…"}
     ],
     "title_parse": {"separators": ["vs", "@", "against", "v", "—"]},
     "categories": [
       {"id": "sports", "color": "#2563eb", "google_color_id": "9"}
     ]
   }
   ```

   - `match[]` stays backward-compatible for followed-team needles
     (Northbridge / Harbor). Substring match still hits titles prefixed with
     🏈 or ⚽.
   - `teams[]` is any team id (opponents included) with `aliases` +
     `logo_url`. Prefer the **longest** alias that appears in that side
     of the title (`AFC Bayport` beats `Bayport`).
   - Home parses **both** sides of `vs` / `@` / `against` / `v` / `—`.
     Two crests when both teams are in the map; one crest when only one
     is known. Missing opponent logo = no second crest.
   - Category color is a left border on This week + On the horizon (not a
     new tab). `categories[]` hex + `google_color_id` win when present on
     the event; otherwise infer from crests / title heuristics.

   Default category hex (override via `categories[]`):

   | id | Default hex | Google color id |
   |---|---|---|
   | `sports` | `#2563eb` | 9 |
   | `music` | `#be185d` | 4 |
   | `family_friends` | `#059669` | 10 |
   | `travel` | `#d97706` | 6 |
   | `other` | `#6b7280` | 8 |

   Heuristics when no Google color id: sports if a crest matched, 🏈/⚽,
   or sports keywords; music if gig/rehearsal/concert/band; travel if
   flight/airport/IATA hop; family/friends for people-ish titles; else
   other.

Python helper: `CalendarStore.save(...)` / `CalendarStore.home_lists()`.

### Enqueue a queue item

Do not invent a new store. Use the module that already owns the kind:

| Kind | Write |
|---|---|
| X follow / post / reply | `ops/queue/x-activity/{YYYY-MM-DD}.json` — `{ date, candidates }` |
| Meme daily candidate | `ops/queue/daily-candidates/{YYYY-MM-DD}.json` |

Every item must include:

- `id` — stable
- `kind`
- `status`: `pending` on create
- `project` — a tenant project id (not `shared` / `unallocated` unless
  the work truly is overhead; prefer a real bet)
- `created_at`
- module payload (`body`, `target`, image fields, …)

The app will not post, buy, or publish as a side effect of the write.
The human reviews X drafts on `/x/`. Meme daily candidates stay in
a separate private application.

### Update a routine row

Write `ops/grok-bot/routines.json`. Set `owner_agent`, `last_run_at`,
`status`, and optionally `project_id`. The `/grok-bot/` page does not
start or stop jobs.

---

## New installation quickstart

The point of this release: a stranger can stand up **their** life ops
app with their own configuration.

1. **Create an independent private copy** using the
   [onboarding guide](onboarding/start-here.md). Personal configuration and records
   stay outside public source control.
2. **Copy the example tenant** and put your bets in it:

   ```bash
   cp config/tenant.example.yaml config/tenant.yaml
   ```

   Edit `human`, `site.domain`, `projects`, and optional `folders`.
   Leave `shared` / `unallocated` out. Leave `last_done` / `next_steps`
   null if you do not know them. `config/tenant.yaml` is gitignored.

   For a deploy with S3, Helper Agent (or you) uploads that file to
   `ops/tenant.yaml`. Do not put secrets in it.

3. **Secrets** — the supported runtime interface is environment variables.
   Use your chosen secret manager to supply them; the reserved secret-backend
   adapters are not implemented. For localhost:

   ```bash
   cp .env.example .env
   ```

   A board-only instance needs no provider keys. Optional S3:

   ```
   OPS_BUCKET=your-private-bucket
   AWS_DEFAULT_REGION=us-east-1
   ```

   Without a bucket, the board lives at `data/projects/board.json`.

4. **Run locally**

   ```bash
   python -m pip install --require-hashes -r requirements.txt
   python web/run.py --local
   # http://localhost:5050  → Home, then Projects
   ```

   You should see your projects in a list (not five empty swim lanes).
   Home is Waiting on you above This week / On the horizon — no hub cards.
   Spend is empty (`{subscriptions: []}`) until you add a local
   `data/tech_spend.json` (gitignored) or upload `ops/spend/tech_spend.json`
   to the bucket. Calendar widgets say “No calendar snapshot yet.” until
   an agent writes the snapshot or you set `CALENDAR_ICS_URL`.

5. **Hosting (optional)** — first complete the
   [authentication guide](onboarding/authentication.md) and the storage/backup
   checks in [Start here](onboarding/start-here.md). For Fly, copy
   `fly.example.toml` to a private `fly.toml` and select your own app name.
   Hosted startup requires the generated login settings. Never deploy local mode.

6. **Cloudflare Access (optional)** — put Access in front of the hostname
   for additional identity/MFA protection. The app's owner login remains required;
   any alternate provider hostname must also remain protected.

7. **Agents** — point Grok Bot / Codex / whatever you already run at the
   board and queue contracts above. The app will not provision agents.

`TENANT_CONFIG=/absolute/path/to/tenant.yaml` wins over S3 and the local
file (useful in tests or a second checkout).

---

## Non-goals (this release)

- Multi-tenant SaaS, orgs, invites, or billing
- A sixth primitive
- Changing an existing production deployment as part of setup
- Copying the meme generation / Imgflip / video / RAG pipeline
- Rewriting the X, Spend ledger, or Grok Bot catalog UIs
- In-app Google OAuth or a live Google Calendar API (snapshot / ICS only)
- Implementing the AWS or Bitwarden secrets backends
- Starting / stopping Grok Bot routines from `/projects/` or Home
- Posting to X, buying, or canceling subscriptions
- Invented `last_done` / `next_steps`, spend figures, X drafts, or
  routine rows
- Hardcoded `waiting_on_owner` product copy
- Project rows for `shared` / `unallocated`
- Example Gym (or any other) project that is not in the tenant file
- Committing an operator `config/tenant.yaml` or a personal spend ledger
- Multi-tenant SaaS (one human, one tenant file, optionally uploaded to S3)


## Display caching

Projects display reads have a 15-second per-worker cache. Edits always read fresh
storage. Saves invalidate the writer's cache, and a local file timestamp also
invalidates sibling workers; external agent updates appear after the TTL on a
subsequent page request. Returned records are copied so a view cannot mutate the
cache. Calendar snapshots retain their 30-second cache.

Shared CSS and JavaScript use content-versioned URLs and private browser caching.
A new build changes the URL when file contents change. Private pages, API responses
and the owner's theme use `no-store`; personal data must not enter a shared CDN
cache. Weather has its own 20-minute forecast cache and loads after Home renders.

A host configured to stop every idle machine still has a cold-start delay. Keeping
one machine running removes that delay at the cost of additional runtime charges;
choose that tradeoff explicitly for each installation.
