# Moving an older private installation to this starter

Do not deploy this source over an existing personal application without an
inventory, a backup, and a staged test. Private modules and workflows may exist in
the old app and are not copied into this core.

- Production startup now requires the generated authentication settings. Follow
  the login guide and verify HTTPS and every hostname. `local_only=True` is never
  a production migration workaround.
- Browser writes require login, a session-bound CSRF token and a JSON object.
  A skip request sends `{}`. Update custom clients rather than disabling protection.
- Inline JavaScript and remote scripts are blocked by CSP. Move private event
  handlers into self-hosted JavaScript files; preserve data attributes and escaping.
- Imported links accept HTTP(S), with safe relative paths only for navigation.
  JavaScript/data/file URLs and credential-bearing links are discarded.
- `LIFE_OPS_AWS_COSTS=true` explicitly enables cost reads. The former presence of
  an AWS key pair no longer enables them. Profiles and roles now work as well.
- Configure `LIFE_OPS_USAGE_PROVIDERS` for existing producers. Untagged xAI events
  now appear as Unallocated by default. To preserve an old installation's implicit
  mapping, set `LIFE_OPS_LEGACY_XAI_PROJECT` to its actual project ID (for example
  `memes`) and verify totals. Do not apply that old assumption to another installation's data.
- Confirm `{provider}-tokens` and `aws` row replacement behavior; failed or
  unpriced sources retain manual fallback costs. Saved trial labels no longer
  depend on a provider's name.
- Runtime dependencies and development tools now have separate hashed locks.
  Containers run as UID/GID 10001; mounted data and instance directories must be
  writable by that identity. Existing root-owned volumes need an explicit migration.
- Private CSS belongs in `instance/theme.css` and must be provisioned separately
  for hosted deployments. It is excluded from public exports and container images.

Use an isolated staging instance with fictional records to verify authentication,
approved writes, source fallback, project allocations and themes. Only migrate
private records after those checks and a restore test pass. Keep the previous
deployment available for rollback until the owner verifies the new one.
