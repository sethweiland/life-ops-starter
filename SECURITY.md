# Security policy

Life Ops is an early single-owner, self-hosted project. Only the latest published
release is intended to receive fixes; no release or response-time commitment is
made until a maintainer publishes one. It is not a multi-user service and has not
had an independent penetration test. Do not use it as a secrets vault or grant it
broad financial or account-control permissions.

## Report a vulnerability privately

On the project's GitHub page, use **Security → Report a vulnerability** when the
maintainer has enabled private reporting. Do not open a public exploit issue or
attach real records, keys, session cookies or private URLs. If private reporting
is unavailable, open an issue requesting a private contact without including the
vulnerability details; wait for a private channel before sharing them.

Include the affected revision, a fictional reproduction, expected/actual behavior,
and possible impact. Maintainers should acknowledge and triage privately, coordinate
a fix, publish an advisory when appropriate, and identify affected/fixed versions.

## Supported trust boundary

- One owner per installation and storage namespace. Sharing an owner key grants
  the same access to the entire dashboard; there are no per-user permissions.
- Production runs through `wsgi:app` with authentication settings and HTTPS.
  `web/run.py --local` is a local demo, never an internet deployment or tunnel.
- The app authenticates private routes, checks session-bound CSRF tokens for
  writes, expires sessions after eight hours and limits request bodies.
- A trusted proxy may supply the HTTPS scheme only when explicitly configured.
  The app does not accept proxy identity assertions as a login.
- Calendar URLs and private CSS are owner-controlled configuration. Imported
  event text and links are untrusted display data. Scripts load from the app;
  inline handlers and remote scripts are blocked by CSP. Styles permit inline CSS
  for existing layout and configurable colors; this is not full CSS isolation.
- Optional weather sends only configured, rounded coordinates to a fixed HTTPS
  provider. It never discovers the owner's location. The summary endpoint requires
  authentication, and disabling the module prevents provider requests.
- External agents have their own credentials. The dashboard records approval;
  each agent must enforce its own authorization before acting on that approval.
- Signed cookie logout removes the current cookie; a stolen copy can survive
  until expiry. Rotate both login settings and restart every worker to revoke
  existing sessions. See [authentication](docs/onboarding/authentication.md).

## Release and maintenance controls

CI runs tests, dependency audits, source scanning and redacted secret scanning.
CodeQL and Dependabot configuration are included, but GitHub features, private
reporting and protected branches must also be enabled and checked by a maintainer.
Passing scans do not establish absence of vulnerabilities or personal content.

Maintain a reviewed, history-free export. Scan the exact candidate, review its
license and attribution, then follow the [release checklist](docs/releasing.md).
Use [credential guidance](docs/onboarding/secrets.md) and least-privilege storage
policies. Backups, restoring records, account security and provider charges remain
the installation owner's responsibility.
