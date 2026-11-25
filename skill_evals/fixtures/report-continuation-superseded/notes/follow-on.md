# Follow-on question, 2026-11-20

User: If the reader was deadlocked, why does the replay job report finishing files during the stall?

Agent: The retained progress counters for the same window W1 show replay completing about 35
files per minute and no lock-wait cycle. The throughput metric counts only files published to
the output queue, and replayed files bypass that queue, so zero throughput did not mean the
reader stopped. The replay-deadlock explanation is disproved; the reader was busy replaying.
Evidence: evidence/progress-counters.json.
