# Credentials and secret storage

You do not need AWS or a secret manager to try Life Ops locally. Choose a storage
method based on where the process runs and which services it actually calls.

## Terms you will encounter

| Term | Meaning in this setup |
| --- | --- |
| Account | Your ownership/login at a provider |
| API key or token | A credential used by software; its permissions and lifetime matter |
| Environment variable | A named value supplied to a running process |
| `.env` | A local file the development entry point reads into its environment; not encrypted storage |
| Secret manager | A service that stores sensitive values and controls retrieval |
| AWS identity / role / profile | How software proves who it is before requesting AWS access |
| Secret ARN | An identifier for an AWS secret, not the value itself |
| S3 bucket | Where the dashboard's private records can live; distinct from secret storage |

## Supported choices today

| Choice | Fit | Current Life Ops behavior |
| --- | --- | --- |
| Private local `.env` | Initial local setup | `web/run.py` and `wsgi.py` load it; existing environment values take precedence |
| Hosting provider's environment secrets | A hosted installation | Works with the `env` backend; follow the host's identity/access controls |
| AWS Secrets Manager | You already use AWS and want central retrieval | Partial helper support through `APP_SECRET_ARN`; details below |
| Another manager that injects environment variables | You already have a supported launcher/injector | The app reads the supplied variables; the manager integration is yours to configure |
| `secrets.backend: aws` or `bitwarden` in tenant YAML | Future direct adapters | **Not implemented. Keep `secrets.backend: env`.** Selecting a name does not connect a vault |

Use your provider's supported credential mechanisms. For AWS workloads, prefer
appropriate roles and temporary credentials; Boto3 also supports configured profiles
for local development. See the [Boto3 credential guide](https://docs.aws.amazon.com/boto3/latest/guide/credentials.html).

## Local environment setup

Copy `.env.example` to `.env`, then enter only the settings you need in a local
editor. Never replace the example file with your real values. Keep `.env` private
and restrict access on a shared computer. The repository ignores it, but already
tracked secrets remain in history until addressed separately.

The dashboard usually does **not** need your AI provider key. If an external agent
calls the model and writes a project update, the key belongs in that agent's runtime.
The dashboard only needs access to the resulting record.

## AWS identity comes before Secrets Manager

The app needs an AWS identity **before** it can read an AWS secret. Storing the only
AWS login credentials inside that secret cannot solve this initial authentication.

For a local profile with IAM Identity Center already available in your account:

```bash
aws configure sso --profile life-ops
aws sso login --profile life-ops
aws sts get-caller-identity --profile life-ops --query Account --output text
```

Check the account output privately, then set `AWS_PROFILE=life-ops` for the app.
The SSO wizard requires your account's portal/session information; it is not a
universal setup for every new AWS account. Follow the
[AWS setup guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
or use the identity method supported by your hosting environment.

Avoid adding permanent access keys solely to work around an app integration gap.
Temporary environment credentials require the matching `AWS_SESSION_TOKEN` as well
as the key pair. Signing into the AWS website alone does not authenticate Boto3.

## Optional AWS Secrets Manager recipe

1. Establish and verify the runtime's AWS identity using the preceding section.
2. In Secrets Manager, create a secret for this installation, using a JSON object.
   Record its region and ARN privately. Account for provider costs before enabling it.
3. Grant that identity `secretsmanager:GetSecretValue` on that specific secret. If
   using a customer-managed KMS key, also configure the required decrypt access.
4. Supply `APP_SECRET_ARN` and `AWS_REGION` in the runtime environment. Keep the
   tenant setting `secrets.backend: env` for this release.
5. Verify retrieval without printing values. Restart after changing secret contents:
   the current helper caches a successful retrieval for the process lifetime.

AWS recommends limited access to secrets and provides the required retrieval
permissions in its [Python retrieval guide](https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets-python-sdk.html)
and [security guidance](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html).

**Current limitation:** only settings read through `src/core/secrets.py` use this
helper. S3 settings such as `OPS_BUCKET` can be read from the JSON secret. The
calendar's `CALENDAR_ICS_URL` is read directly from the process environment and
must be supplied there, for example through a host secret or your manager's injector.
Putting arbitrary keys in the JSON secret does not make them environment variables.

For helper-managed values, a nonempty secret value wins over the environment value.
If retrieval fails, the helper silently falls back to the environment. Therefore
"the app starts" is **not** proof that Secrets Manager worked. The offline checker
deliberately marks this connection unverified. A coding agent can perform an
authorized, read-only retrieval check and report only success/failure and expected
key presence; it should not print `SecretString` or values.

## Rotation, revocation and disconnection

Record the owner, purpose, storage location, permission scope and last verification
date in your private checklist—never the credential value. When changing a key:
create/update it at the provider, update the runtime's secret source, restart if
required, verify the intended operation, then retire the old key. Some providers
invalidate the old credential immediately; follow that provider's procedure.

To disconnect, remove the runtime setting and revoke its provider access when no
other process needs it. Removing the local setting does not revoke a provider key.
If a secret has been exposed, replace/revoke it at the provider; removing a public
file is not sufficient. Avoid posting full exception messages or calendar feed URLs.
