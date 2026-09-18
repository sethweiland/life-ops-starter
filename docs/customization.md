# Make Life Ops your own with a coding agent

The app is ordinary Python, Flask, Jinja templates, CSS and small JavaScript files.
There is no frontend build pipeline to learn for a theme change. A coding agent
can help substantially with layout and styling, but the result still needs a
browser check, and new account integrations need real implementation and testing.

## Start with your own private copy

When the public repository is marked as a template, choose **Use this template →
Create a new repository → Private**. Alternatively, download the reviewed release
into a new private repository. GitHub documents [template creation and visibility](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template).
Do this before adding personal configuration or records. Keep the starter version
you began with in a private note so future security updates can be compared.

This release is a source starter, not an installed package with a complete plugin
API. Your private copy can diverge; upstream updates need to be reviewed and
merged or applied as patches. A separate packaged core/private-extension system
is future work. Don't publish your private repository to contribute a fix—copy
only the generic change and a fictional test into a clean public checkout.

## Three levels of customization

| Change | Start here | Verification |
| --- | --- | --- |
| Name, timezone, projects, modules, agents, bookmarks | `config/tenant.yaml` | Restart and check names, dates, enabled pages |
| Colors, typography, spacing, visual style | `instance/theme.css` plus the CSS variables in `web/static/style.css` | Check Home, Projects, Spend and mobile width |
| Page layout, a new view, or a connector | `web/templates/`, `web/static/`, `web/blueprints/`, `src/core/` | Behavior/security tests, a browser check, updated contracts and setup docs |

An optional theme example is `examples/theme-forest.css`. Create the private
`instance` directory, copy the example to `instance/theme.css`, and reload. The
server serves only that fixed CSS file behind normal authentication. It is excluded
from Git, public exports and images. On a hosted instance, provision it separately
in private persistent storage; copying it on your laptop does not deploy it.

The variables are a starting palette, not a complete design system. Some component
styles still use local colors. For a full redesign, have your coding agent update
those components consistently in your private copy. Keep contrast, keyboard focus,
responsive tables, loading/error states and readable long titles in the brief.
Fonts and scripts must be self-hosted under the app's browser security policy.

## Prompts to copy into Codex or another coding agent

**First setup**

> Read AGENTS.md, README.md and docs/onboarding/start-here.md. Help me run this
> private copy locally with no cloud accounts. Ask which three outcomes I want on
> my dashboard. Configure only the relevant modules. Use fictional records to
> verify each page. Keep personal data and secrets out of commits and chat.

**Visual redesign**

> Read docs/customization.md. Restyle my private Life Ops dashboard with a calm,
> editorial layout, warm colors and clear typography. Start with instance/theme.css;
> update templates only where needed. Preserve authentication, CSRF, safe links,
> keyboard use and the JSON contracts. Show the result with fictional data at a
> phone width and a desktop width, and verify a project status edit still works.

Replace the visual direction with your own. A screenshot can be helpful, but use
a fictional screen or remove personal records before sharing it with any service.

**Connect Spend**

> Read docs/onboarding/spend.md. Help me add one manual subscription first. Then
> identify the exact source for each cost I want: a ledger, application usage logs,
> or AWS Cost Explorer. Explain permissions and cost before connecting anything.
> Guide me through entering credentials locally; don't ask me to paste them here.
> Verify known amounts and show disconnected, missing-price and failed states.

**Add a module**

> Read docs/primitives.md and the data contracts. Propose the smallest private
> module for [my workflow]. Identify the data owner, read/write permissions,
> retention, verification and failure behavior. Use a module flag and fictional
> fixtures. Keep all routes behind login and all writes behind CSRF. Document setup
> and disconnection. Don't imply a provider is connected until a real check passes.

## Update safely

Before an upstream update, back up private data and record the current revision.
Review migration notes, test with fictional copies, and keep your private theme
separate. Run `pip install --require-hashes -r requirements-dev.txt` and
`python -m pytest`. Only then deploy through your private installation's process.
