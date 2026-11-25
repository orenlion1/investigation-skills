# Queue consumer lag after the nightly batch

Synthetic fixture, not production findings. Report formats: Markdown only.
Parent task: [TASK-example.md](../tasks/TASK-example.md)

## Key findings

The batch publishes faster than the consumers drain; lag returns to zero about forty minutes later. [E1](#E1)
The cause is a candidate: consumer concurrency is fixed at four. [E2](#E2)

## Proposed remediation

| Change | Status |
| --- | --- |
| Scale consumer concurrency with queue depth | Proposed, not implemented |

## Evidence index

Source: synthetic queue metrics, 01:00-03:00 UTC; read-only; evidence window closed at 03:00 UTC.

- <a id="E1"></a>E1 - Queue depth and consumer lag samples.
- <a id="E2"></a>E2 - Consumer configuration, concurrency 4.

## Token usage

Accounting cutoff: end of the investigation session; publication is not counted.
