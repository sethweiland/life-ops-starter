# Prepare a separate shareable starter

Never make an owner's existing private repository public. It may contain personal
history even when the working tree looks generic. The public starter begins with
a fresh export and a new repository. Personal installations keep their own private
configuration, data, deployment and customization history.

## Candidate gate

- [ ] Select a license, confirm ownership/third-party attribution, and include LICENSE.
- [ ] Install the hashed development requirements and pass the full tests.
- [ ] Run runtime/development dependency audits and Bandit; review every finding.
- [ ] Build a new directory with `scripts/export_public.py` and scan that exact
  directory with Gitleaks. Review all manifest additions, examples and docs for
  personal information that secret-pattern scanners cannot recognize.
- [ ] Verify first boot without accounts in explicit local mode, and refusal to
  start the hosted entry point without login configuration.
- [ ] Verify authenticated read/write, anonymous denial, alternate-host denial,
  CSRF rejection, and a private credential-rotation procedure.
- [ ] Complete the fictional USD 18 Spend example and a themed browser edit.
- [ ] Build/run the Docker image, verify the non-root runtime and durable storage,
  and check the real deployment's HTTPS/proxy arrangement before recommending hosting.
- [ ] Have another person follow onboarding from a clean machine. Record gaps
  using fictional data. A second security review is encouraged before stable release.

Use a new output name each time; the exporter refuses overwriting a candidate.
PUBLIC_FILES.sha256.json describes exactly what was copied. Do not initialize Git
in the original repository or include its .git directory in the candidate.

## GitHub setup after the candidate is approved

Create a new repository for the exported files, initially private for review if
needed. Review the initial commit and file list before making that new repository
public. Mark it as a template so adopters can create independent private copies.
Publishing the starter does not invite anyone into an existing private installation.
Only send individual invitations or messages when the owner has authorized them.

Enable private vulnerability reporting, Dependabot alerts, secret scanning and
push protection where available. Require the Test public core, Security checks
and CodeQL jobs and reviewed changes on main. Verify settings in GitHub; YAML
files alone do not enable every platform feature. See [GitHub's security quickstart](https://docs.github.com/en/code-security/getting-started/quickstart-for-securing-your-repository).

CI includes pinned action commits and a checksum-verified secret scanner. The
scheduled security checks detect newly disclosed dependency issues; configure a
maintainer who will actually read and act on the alerts. Private repositories may
need the appropriate GitHub plan for some scanning features.
CodeQL is skipped in private copies by default; an eligible private repository can
opt in with the repository variable `LIFE_OPS_ENABLE_PRIVATE_CODEQL=true`. The
tests, dependency audits, Bandit and Gitleaks still run in private copies.

Publish an initial preview only with explicit limitations: single owner, no built-in
MFA, no bank or general invoice sync, no scheduler, no automatic model-account
connection, and no complete plugin/package separation yet. A preview is useful for
an early adopter; it is not a certification or a claim of universal deployment safety.

## Public onboarding

Share the new repository/release link, [Start here](onboarding/start-here.md),
[Customization](customization.md), and [Spend setup](onboarding/spend.md).
Anyone can create a private copy, open it with their coding agent, complete local
setup and one fictional edit, then connect one real source at a time.
They use their own accounts, bucket, access key and deployment; none of the original
owner's credentials, records or infrastructure are part of the handoff.
