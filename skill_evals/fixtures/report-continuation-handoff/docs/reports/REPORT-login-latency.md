# Login latency investigation

Synthetic fixture, not production findings. Status: in progress.

## Key findings

p95 login latency rose from 180 ms to 950 ms at 2026-11-16T09:00Z. [E1](#E1)
Summary written 2026-11-17: the regression is probably caused by the password hashing cost
increase; not yet verified.

## Continuation record

Coverage: Q1 to Q2 only (summary written 2026-11-17).

| Entry | Date | User question or decision | Agent response and disposition |
| --- | --- | --- | --- |
| Q1 | 2026-11-17 | When did login latency regress? | Answered: 2026-11-16T09:00Z. [E1](#E1) |
| Q2 | 2026-11-17 | Is the hashing cost change responsible? | Provisional: timing matches; not verified. |

## Evidence index

| ID | Source | Window |
| --- | --- | --- |
| <a id="E1"></a>E1 | [login latency](../../evidence/login-latency.json) | 2026-11-16T06:00Z to 12:00Z |
| E2 | CPU flame graph, `../../../captures/identity-flame.svg` | 2026-11-18T10:00Z to 10:15Z |
| E3 | Hashing benchmark notes, `/home/analyst/scratch/hash-bench.txt` | 2026-11-18 |
