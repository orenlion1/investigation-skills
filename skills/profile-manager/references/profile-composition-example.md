# Profile composition: worked example

The repository test suite executes the commands between the markers verbatim and compares the
result with the Resources shown below, so this file stays true to the helper. All values are
synthetic. The rules are in [profile-store.md](profile-store.md#profile-composition).

Create the store and the environment profile:

<!-- profile-composition-example:start -->
```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . ignore
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . init
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  set --profile prod-us \
  --field AWS_ACCOUNT=demo-prod-us-readonly \
  --field AWS_REGION=us-east-1 \
  --field GRAFANA_CONTEXT=demo-prod-us \
  --field SLACK_CHANNEL='#demo-ops' \
  --field PUBLISH=https://example.atlassian.net/wiki/spaces/OPS/pages/123/Investigations \
  --field REPO=https://github.com/demo-org/shared-config \
  --field 'RHYMING_ENDPOINTS=[{"id":"prior-work","kind":"confluence","target":"https://example.atlassian.net/wiki/spaces/OPS/pages/456/History"}]'
```

Create the application profile, with several repositories and Slack channels:

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  set --profile app-alpha \
  --field 'REPO=["https://github.com/demo-org/app-alpha","https://github.com/demo-org/app-alpha-lib"]' \
  --field 'SLACK_CHANNEL=["#demo-app","#demo-library"]'
```

Compose both into a named snapshot, then load it into the `docs/tasks/TASK.md` draft:

```sh
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  compose --profile prod-us --profile app-alpha --into prod-us-app-alpha --dry-run
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  compose --profile prod-us --profile app-alpha --into prod-us-app-alpha
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  render --profile prod-us-app-alpha
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  load --profile prod-us-app-alpha --task docs/tasks/TASK.md --dry-run
python3 -B skills/profile-manager/scripts/profile_env.py --repository-root . \
  load --profile prod-us-app-alpha --task docs/tasks/TASK.md
```
<!-- profile-composition-example:end -->

The effective task Resources are:

```markdown
## Resources

- Repo (Bitbucket/Github): `https://github.com/demo-org/shared-config`
- Repo (Bitbucket/Github): `https://github.com/demo-org/app-alpha`
- Repo (Bitbucket/Github): `https://github.com/demo-org/app-alpha-lib`
- Slack channel: `#demo-ops`
- Slack channel: `#demo-app`
- Slack channel: `#demo-library`
- AWS account: `demo-prod-us-readonly`
- AWS region: `us-east-1`
- Grafana context: `demo-prod-us`
- Grafana Assistant: `enabled`
- Publish: `https://example.atlassian.net/wiki/spaces/OPS/pages/123/Investigations`
- Rhyming endpoints: `[{"id":"prior-work","kind":"confluence","target":"https://example.atlassian.net/wiki/spaces/OPS/pages/456/History"}]`
- Rhyming historical window days: `7`
- Generate PDF: `enabled`
- Fan-out: `enabled`
```
