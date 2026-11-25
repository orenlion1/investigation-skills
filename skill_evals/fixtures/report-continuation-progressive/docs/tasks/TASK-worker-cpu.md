# Task Title: Worker CPU alert investigation

Synthetic fixture for a continuation exercise. Stay offline: do not query external services,
send messages or publish.

## Problem

Explain the recurring worker CPU alert transitions on the example worker fleet.

## Acceptance Tests

- [x] Explain the alert transition mechanism from the saved alert evidence.
- [ ] Identify the CPU workload behind the alert.
- [ ] Validate any candidate mechanism against the application source.

## Resources

- Grafana context: `example-staging`
- Alert evidence: [alert transitions](../../evidence/alert-transitions.json)
- Application repository: `https://git.example.invalid/example/worker-app` (added after first delivery)
- Generate Markdown: `enabled`
- Generate PDF: `disabled`
- Generate HTML: `disabled`

Canonical report: [worker CPU investigation](../reports/REPORT-worker-cpu.md).
