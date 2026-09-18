# What belongs on a personal dashboard

Keep the first installation small: projects you care about, upcoming events,
decisions waiting for you, and costs you want to understand. Enable another page
only when it has a useful source. Empty sections are honest and can be hidden.

## The five primitives

| Primitive | Question it answers | Current representation | Example |
| --- | --- | --- | --- |
| Project | What am I trying to move forward? | Stable id, name, status, summary, last done, next steps, links, optional owner | Plan a trip, publish an essay, maintain the house |
| Queue item | What work is ready for review? | Dated candidate with id, content, status and project | Review a draft reply; the built-in queue currently uses X-shaped records |
| Human gate | What have I explicitly approved? | Approve/skip state or a project status change | Approve a draft; execution stays with a separately authorized agent |
| Cost event | What did this activity or service cost? | Subscription ledger or token event, tagged to a project | Annual domain fee, shared hosting, a model call |
| Routine | What recurring work exists, and when did it run? | Catalog of schedule, owner, last run and project | Weekly review, subscription check, travel reminder |

The calendar is a view of events from a snapshot or read-only ICS feed. It does
not create a separate task system. Folders are navigation links, not another
database of work. A routine entry documents a schedule; it does not schedule a job.
Weather is another optional Home view: umbrella, rain-jacket and clothing cues for
the upcoming hours. It uses a privately configured location and needs no new
primitive. See [Weather setup](onboarding/weather.md).

These are enough to start a personal dashboard without inventing a separate
database for every page. They are not a restriction on your private installation:
add new record types when a workflow needs them. The [roadmap](roadmap.md) separates
available features from useful next improvements.

## Make projects useful without turning them into a task manager

Give each project a stable id and a concrete outcome. Keep the summary to a few
sentences, last_done factual, and next_steps specific enough that you know what
to do next. Assign an agent only when that agent actually exists in your setup.
Use links for supporting material instead of copying sensitive documents into cards.

| Status | Use when |
| --- | --- |
| Idea | You are considering the project |
| Active | Work is in progress |
| Blocked | Something external must change |
| Waiting on you | A decision or action is yours |
| Parked | You deliberately paused it |

Home prioritizes Waiting on you. The board edits status today; adding projects and
changing summaries happens through private configuration or a record-writing agent.
There is no built-in task checklist, due-date field, project completion archive,
notification engine, or general CRUD editor yet. Don't describe these as available.

`shared` and `unallocated` are spending categories, not projects. Missing cost
tags remain visible as Unallocated. Avoid inventing project attribution to make
the graph look tidy.

## Common starting configurations

- **Personal planning:** a few active projects, upcoming calendar events and a
  weekly-review routine. Keep Spend and draft review hidden until needed.
- **Independent builder:** projects, subscription ledger, provider usage logs,
  and a deployment link for each active project.
- **Writer or creator:** publication projects, agent-written draft candidates,
  calendar deadlines and publishing-tool subscriptions. Actual publishing is a
  separate explicit action outside the dashboard.
- **Household admin:** maintenance projects, shared calendar and recurring bills
  recorded manually. One owner account is supported; family member permissions
  require a separate feature, not sharing a supposedly limited login.

Habit streaks, journals, shopping, health metrics and net-worth views may be useful
private modules later. Add one when it has a defined daily workflow, a data source,
and a reason the current primitives do not fit. Health and financial integrations
need their own access and retention decisions. They are not part of this starter.

Use [the data contracts](life-ops.md) when implementing a module, and
[the customization guide](customization.md) for the smallest safe change.
