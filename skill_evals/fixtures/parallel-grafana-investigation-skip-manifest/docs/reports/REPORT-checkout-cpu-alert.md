# Checkout CPU alert investigation

## Key findings

- The alert rule `checkout-cpu-high` fired 4 times between 2026-11-19T10:00:00Z and
  2026-11-19T11:00:00Z UTC in Grafana context `ops` (production).
- Direct gcx reads show checkout pod CPU above the 85% threshold for 38 of 60 minutes.
- The Grafana Assistant branch suggested a batch job overlap; the direct reads have not yet
  confirmed that lead.

## Evidence index

| ID | Evidence | Branch |
| --- | --- | --- |
| E1 | Alert state history for `checkout-cpu-high`, 10:00-11:00Z | direct gcx |
| E2 | `sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="checkout"}[5m]))` | direct gcx |
| E3 | Assistant conversation summary (lead only) | Grafana Assistant |

## Source

- Grafana context: `ops`, environment `production`
- Window: 2026-11-19T10:00:00Z to 2026-11-19T11:00:00Z (UTC)
- Task: none (ad hoc request)
