# Task Title:

## Problem

Enter problem statement.

## Acceptance Tests

At least one acceptance test is required.

- [ ] Enter an observable, testable condition.

## Resources

Each setting is optional. Specify at least one actual resource; omit or leave blank
the settings that do not apply. Placeholders and examples do not count as resources.

REPO, SLACK_CHANNEL and PUBLISH profiles accept a single value or a JSON array (up to
16 unique entries, 512 characters each, 8 KiB per field). Loading arrays emits one Repo,
Slack channel or Publish bullet per entry; keep every supplied resource in the saved
section. Each Publish bullet is one destination: a Confluence page or a repository.

- Repo (Bitbucket/Github): `<enter repo name>` (example: `example-service`)
- Slack channel: `<enter channel name or channel ID>` (examples: `#example-support` or `C0123456789`)
- AWS account: `<enter AWS profile>` (example: `team-readonly`)
- AWS region: `<enter AWS Region>`
- Grafana context: `<enter gcx profile>` (example: `example`)
- Grafana Assistant: `<enabled or disabled>`
- Alert: `<Alert name>`; UID `<Enter UID>`
- Publish: `<Parent page or repository>` (examples: Confluence page "Investigations" or `https://github.com/example-org/example-reports`)
- Rhyming endpoints: `<JSON endpoint array>`
  <!-- grafana-assistant-search uses id/kind/target/context for scoped Assistant matching;
       grafana-assistant-conversations remains history-only. Assistant disabled suppresses prompts. -->
- Rhyming historical window days: `<positive integer days>`
- Generate PDF: `<enabled or disabled>`
