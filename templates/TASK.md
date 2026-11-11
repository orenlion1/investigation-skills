# Task Title:

## Problem

Enter problem statement.

## Acceptance Tests

At least one acceptance test is required.

- [ ] Enter an observable, testable condition.

## Resources

Each setting is optional. Specify at least one actual resource; omit or leave blank
the settings that do not apply. Placeholders and examples do not count as resources.

REPO profiles accept a single repository or a JSON array (up to 16 unique entries,
512 characters each, 8 KiB total). Loading an array emits one Repo bullet per entry;
keep every supplied repository in the saved Resources section.

- Repo (Bitbucket/Github): `<enter repo name>` (example: `example-service`)
- Slack channel: `<enter channel name or channel ID>` (examples: `#example-support` or `C0123456789`)
- AWS account: `<enter AWS profile>` (example: `team-readonly`)
- AWS region: `<enter AWS Region>`
- Grafana context: `<enter gcx profile>` (example: `example`)
- Alert: `<Alert name>`; UID `<Enter UID>`
- Publish: `<Parent page>` (example: Confluence page "Investigations")
- Rhyming endpoints: `<JSON endpoint array>`
  <!-- grafana-assistant-search uses id/kind/target/context for scoped Assistant matching;
       grafana-assistant-conversations remains history-only. Assistant disabled suppresses prompts. -->
- Rhyming historical window days: `<positive integer days>`
- Generate PDF: `<T or F>`
