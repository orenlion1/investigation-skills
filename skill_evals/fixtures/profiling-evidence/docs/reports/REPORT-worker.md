# Worker CPU investigation

## Key findings

**Bottom line.** S3 loading and parsing dominate the saved process CPU profile. The triggering
defect and duplicate replay remain unverified. [E1](../../evidence/cpu.json)

## Profiling detail

The saved stack attributes 85% of sampled CPU to `S3Loader.processFile`; event-reader frames
are descendants, not independent CPU populations. [E1](../../evidence/cpu.json)

## Evidence index

Source: offline synthetic saved profile, context ops, worker-4, November 19, 2026,
10:00–12:00 UTC; no live investigation, deployed revision or replay identities available.

- [E1](../../evidence/cpu.json) — saved CPU stack and query metadata. No rendering yet.
