# What you can build

Life Ops is a starting point for your own private life website. The same source
can support a household dashboard, a writing workspace or an independent builder's
operations page. Choose the pages you need and customize their appearance.

## Available today

- Projects with status, summary, last completed work, next steps, links and an
  optional agent owner. You can change status in the browser; other project
  changes use private configuration or the documented record format.
- Home with decisions waiting for you, calendar views and optional weather cues,
  including evening temperatures. Calendar input is a snapshot or read-only ICS.
- Spending from a manual subscription ledger, application-produced model usage,
  and optional AWS Cost Explorer. No bank credentials are needed for the ledger.
- Draft approval and skip states. The built-in draft page currently uses the X
  record shape; a general review inbox would need additional implementation.
- A routine catalog describing recurring work and its last run. Scheduling and
  executing that work belong to your separate tools or agents.
- Private theme CSS, configurable navigation and optional modules. No frontend
  build tool is required for a theme edit.

Start with [the primitives](primitives.md), follow [onboarding](onboarding/start-here.md),
and use the [customization prompts](customization.md) for your first change.

## Next improvements

These are development priorities, not features already included or promised dates:

1. **Everyday project editing:** create, rename, update and archive projects from
   the dashboard, with clear handling of existing agent-written records.
2. **A general review inbox:** use the existing queue and approval concepts for
   travel options, document drafts and other decisions beyond the X-shaped page.
3. **Guided connections:** show which connections are optional, configured and
   actually verified, with useful repair steps and no exposed credentials.
4. **Easier core updates:** package the reusable core with a small extension API
   so private customizations do not require maintaining a divergent source copy.

The existing primitives are enough to begin. Add a new record type when a concrete
workflow needs it: a habit tracker may need check-ins, a journal needs entries,
and a task list may need due dates and completion. Those can begin in optional
private modules; they do not need to become mandatory parts of everyone's dashboard.

## Current boundaries

Each installation has one owner. There are no family/team roles, hosted signups,
automatic account connections, bank sync, habit tracking, notification engine or
built-in agent scheduler. A coding agent can help implement a new module, but it
does not make provider setup or verification automatic.

This is an early public release. Automated checks and fictional setup exercises
do not replace testing with new users or an independent security review. Report
setup problems with fictional reproductions; follow [SECURITY.md](../SECURITY.md)
for vulnerabilities.
