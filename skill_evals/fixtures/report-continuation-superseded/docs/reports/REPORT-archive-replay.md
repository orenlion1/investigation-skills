# Archive replay stall investigation

Synthetic fixture, not production findings. Status: delivered and published 2026-11-04.

## Key findings

Replay of archived files deadlocked the archive reader: throughput fell to zero while replay
was active. [E1](#E1)

## Original metrics

| Time (UTC) | Reader throughput (files/min) | Replay active | Evidence |
| --- | --- | --- | --- |
| 2026-11-03T08:00Z | 120 | no | [E1](#E1) |
| 2026-11-03T08:20Z | 0 | yes | [E1](#E1) |
| 2026-11-03T08:50Z | 115 | no | [E1](#E1) |

Observation window W1: 2026-11-03T07:30Z to 09:30Z.

## Continuation record

| Entry | Date | User question or decision | Agent response and disposition |
| --- | --- | --- | --- |
| Q1 | 2026-11-04 | Why did the reader stop? | Answered: replay deadlock. [E1](#E1) |

## Evidence index

| ID | Source | Window |
| --- | --- | --- |
| <a id="E1"></a>E1 | [reader throughput](../../evidence/reader-throughput.json) | W1 |

## Publication

Published 2026-11-04 to `https://wiki.example.invalid/pages/archive-replay` (page version 1).

## Token usage

Accounting cutoff 2026-11-04T12:00:00Z. Investigation total for revision 1: 41,200 tokens over
52 minutes, from the original session files.
