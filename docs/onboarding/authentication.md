# Private access to your hosted dashboard

Life Ops is one person's private installation. The first supported login uses a
random owner access key, saved in your password manager. There are no shared user
accounts, email resets, or built-in MFA. An identity gateway with MFA can sit in
front as an additional layer; it does not replace the app's login.

## Local demo

Run `python web/run.py --local`, then open http://localhost:5050. This binds to
127.0.0.1 and rejects non-loopback addresses and unexpected Host headers. CSRF
protection still applies. Anyone with access to that computer can open the demo.
Do not expose it through a tunnel or reverse proxy: those can make remote users
appear local. The production `wsgi.py` never enables this mode.

## 1. Generate your login settings

Choose the exact HTTPS address you will use (a provider hostname is fine).
On your own computer, in your private installation, run:

```bash
python scripts/setup_auth.py --origin https://ops.example.com
```

Replace the example address with yours. This creates a new `instance/auth/`
directory, excluded from Git, Docker images and public exports. Existing files
are never overwritten. On POSIX systems the directory is owner-only and files
have mode 600. On Windows, also check that your user account alone has access.

Open `instance/auth/owner-access-key.txt` locally and save its contents as the
password for your site in your password manager. Do not paste it into a coding
agent conversation, public issue, screenshot or deployment log. The generator
does not print secret values. Remove that temporary plaintext file after you
have verified your password manager saved it.

The separate `instance/auth/server.env` file contains:

| Setting | Purpose |
| --- | --- |
| `LIFE_OPS_ORIGIN` | The one allowed HTTPS origin; no path or wildcard |
| `LIFE_OPS_OWNER_KEY_SHA256` | Digest of the generated access key; the raw key is not deployed |
| `LIFE_OPS_SESSION_SECRET` | Independent secret for signing browser sessions and CSRF tokens |

Use the generator's random key, not a human-chosen password. Its 256 bits of
randomness make guessing infeasible; the digest is not a password-hardening
scheme for weak passwords. Store the entire server.env file privately. Upload
these settings through your hosting provider's environment-secret facility.
The APP_SECRET_ARN helper does not supply these authentication settings.

Validate the file without printing its values:

```bash
python scripts/check_setup.py --hosted --env-file instance/auth/server.env
```

This checks format only. It does not verify entropy, TLS, connectivity or login.

## 2. Configure HTTPS and the proxy

The hosted app refuses requests using HTTP or an unconfigured hostname. Configure
your host to redirect browser HTTP traffic to HTTPS and preserve the original
Host header. Without a proxy, leave `LIFE_OPS_PROXY_HOPS=0`.

When exactly one trusted proxy terminates TLS, set `LIFE_OPS_PROXY_HOPS=1`. It must
overwrite X-Forwarded-Proto and the backend must be reachable only through that
trusted proxy. The app trusts only that scheme header, never forwarded user,
address or hostname headers. Do not enable proxy trust for an arbitrary public
backend. The app still requires its own login, even when a proxy asserts identity.
See [Flask's proxy configuration guidance](https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/).

For Fly, the example config enables this one-proxy setting and HTTPS redirects;
Fly documents the [forwarded protocol header](https://fly.io/docs/networking/request-headers/).
After selecting your own app in fly.toml, import the generated settings:

```bash
fly secrets import < instance/auth/server.env
```

Then deploy your private installation using its normal deployment process. Do not
copy the owner's plaintext key into the image. Keep the session secret identical
across workers and restarts. A deployment without valid settings fails to start
before it opens private stores. `/healthz` is the sole public data endpoint and
returns only `{"status":"ok"}`; sign-in and static assets are also public on the
configured origin.

## 3. Verify before adding personal data

Use fictional records for the first check:

1. In a signed-out browser, opening Home or Projects shows the login page. The
   draft JSON API requires login as well.
2. A wrong key is rejected. Your saved key opens the dashboard.
3. Approve or skip a fictional draft and change a project's status. Reload to
   confirm the changes persist.
4. Sign out, then revisit a private URL. It must require login again.
5. Open every alternate hostname, including the provider's default address if
   different from LIFE_OPS_ORIGIN. Private pages must be denied. Test direct origin
   access as well if your host supplies one.
6. Restart the app and confirm existing login and records behave as expected.

Sessions expire after eight hours, including active use. Cookies are Secure,
HttpOnly, host-only and SameSite=Strict. Pages and API responses use no-store.
Login, logout and all edits require a session-bound CSRF token. After an hour,
an old page's token can expire: reload before retrying an edit. Cross-site writes
are rejected. API errors return JSON; an expired login requires signing in again.

HTTPS form protection checks Referer too. The app uses a same-origin referrer
policy; a proxy must not replace it with no-referrer on these pages. A browser
extension that removes Referer may cause safe rejection of writes.

## Recovery and rotation

There is no email recovery. With administrative access to the private deployment,
generate a replacement in a new private folder:

```bash
python scripts/setup_auth.py --origin https://ops.example.com --output-dir instance/auth-next
```

Save the new owner key, replace the deployed server.env settings, and restart all
workers. Changing either the owner-key digest or signing secret invalidates old
sessions on updated workers. Complete the rollout before treating old sessions as
revoked. Keep the proxy setting appropriate to your host.

Sign out removes the current browser cookie. Because sessions are signed cookies,
a stolen copy can remain usable until expiration. Rotate the deployed secrets
to revoke all copies immediately across updated workers.

Do not share the owner key with agents or other people. This is not multi-user
access control. Use the hosting provider's rate limits for abusive traffic, and
keep backups and account permissions scoped separately. Authentication does not
make imported records trusted or replace the remaining release-security work.

Implementation references: [Flask security guidance](https://flask.palletsprojects.com/en/stable/web-security/)
and [Flask-WTF CSRF protection](https://flask-wtf.readthedocs.io/en/1.2.x/csrf/).
