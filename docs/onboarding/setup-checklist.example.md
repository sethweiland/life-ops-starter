# Private setup checklist template

Copy this file into `instance/setup.md` in your private installation. Keep the
original example generic. Record names of secret locations, never secret values.

## First success

- [ ] Local app opens without cloud credentials.
- [ ] Personal timezone/projects are configured and survive restart.
- [ ] Offline checker has no FAIL results.
- [ ] I know which process owns each external connection.

## Connections

| Capability | Needed now? | Responsible process | Account/identity label | Secret location label | Granted access | Last verified | Result | Disconnect procedure |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Calendar | undecided | dashboard or agent | not configured | not configured | none | never | not connected | see calendar guide |
| Weather | undecided | dashboard | no account required | private environment | approximate coordinates only | never | disabled | turn off module and restart |
| Shared records | undecided | dashboard + producer | not configured | not configured | none | never | local only | back up before switching stores |
| Draft producer | undecided | external agent | not configured | not configured | none | never | not connected | stop producer and revoke access |

## Hosting readiness

- [ ] Generated owner key is saved privately; the plaintext setup copy is removed.
- [ ] Hosted login settings pass the offline `--hosted` check.
- [ ] HTTPS and the trusted proxy setting match the hosting arrangement.
- [ ] Intended hostname requires login when signed out.
- [ ] Provider default hostname is also protected or inaccessible.
- [ ] A fictional edit succeeds after login; sign-out prevents subsequent access.
- [ ] I know how to rotate login settings and invalidate existing sessions.
- [ ] Test data persists through a restart and redeploy.
- [ ] Backup and isolated restore have been verified.
- [ ] Provider costs and credential-expiration procedures are recorded.
- [ ] Local and production settings use separate identities/storage where needed.

## Next connection

Desired outcome:

Existing relevant accounts:

Current blocker (sanitized):

Smallest next verification step:
