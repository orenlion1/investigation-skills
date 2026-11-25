# Worker CPU alert investigation

Synthetic fixture, not production findings. Status: delivered 2026-11-10 (first delivery).

## Key findings

The CPU alert flaps because its rule fires on a threshold predicate with a 2-minute pending
period and no recovery hold-down, so short dips below the threshold reset it. [E1](#E1)
The CPU workload behind the high usage is not confirmed.

## Alert timeline

| Time (UTC) | Observation | Evidence |
| --- | --- | --- |
| 2026-11-09T14:02Z | Alert firing, worker CPU above 85% | [E1](#E1) |
| 2026-11-09T14:09Z | Alert resolved after one sample below threshold | [E1](#E1) |
| 2026-11-09T14:13Z | Alert firing again | [E1](#E1) |

## Open questions

- Which workload drives the worker CPU above the threshold?

## Continuation record

| Entry | Date | User question or decision | Agent response and disposition |
| --- | --- | --- | --- |
| Q1 | 2026-11-10 | Why does the CPU alert keep resetting? | Answered: pending period without recovery hold-down. [E1](#E1) |

## Evidence index

| ID | Source | Window |
| --- | --- | --- |
| <a id="E1"></a>E1 | [alert transitions](../../evidence/alert-transitions.json) | 2026-11-09T14:00Z to 15:00Z |

## Source

Report formats: Markdown only. Evidence window W1 is 2026-11-09T14:00Z to 15:00Z.
