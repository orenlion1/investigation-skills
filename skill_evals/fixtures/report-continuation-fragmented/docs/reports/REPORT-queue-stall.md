# Queue consumer stall investigation

Synthetic fixture, not production findings. Status: delivered 2026-11-06.

## Key findings

Consumer lag grew from 0 to 48,000 messages between 2026-11-05T10:00Z and 10:40Z, then
recovered. [E1](#E1) Current conclusion (provisional): long garbage-collection pauses in the
consumers stalled processing.

## Open questions

- Do consumer GC logs show pauses during the stall?

## Continuation record

| Entry | Date | User question or decision | Agent response and disposition |
| --- | --- | --- | --- |
| Q1 | 2026-11-06 | What caused the stall? | Provisional: GC pauses suspected; GC logs not yet inspected. [E1](#E1) |

## Evidence index

| ID | Source | Window |
| --- | --- | --- |
| <a id="E1"></a>E1 | [consumer lag](../../evidence/consumer-lag.json) | 2026-11-05T09:30Z to 11:30Z |
