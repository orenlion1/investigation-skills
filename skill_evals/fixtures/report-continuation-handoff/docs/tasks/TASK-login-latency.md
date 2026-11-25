# Task Title: Login latency investigation

Synthetic fixture for a continuation exercise. Stay offline: do not query external services,
send messages, upload or publish.

## Problem

Explain the login latency regression on the example identity service since 2026-11-16.

## Acceptance Tests

- [x] Show when p95 login latency regressed, from saved latency evidence.
- [ ] Identify the cause of the regression.

## Resources

- Grafana context: `example-prod`
- Generate Markdown: `enabled`
- Generate PDF: `disabled`
- Generate HTML: `disabled`

Canonical report: [login latency investigation](../reports/REPORT-login-latency.md).
