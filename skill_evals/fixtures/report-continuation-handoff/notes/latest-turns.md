# Latest turns (not yet in the report)

Ordered excerpt; earlier turns before 2026-11-17 are not available here.

1. 2026-11-18, user: The hashing cost change was rolled back on 2026-11-17 and latency stayed high,
   so it is not the cause. Correct the report.
2. 2026-11-18, agent: Agreed. The flame graph (E2) shows most time in the session-store client
   waiting on connections, not in hashing. Candidate: session-store connection pool exhaustion;
   not verified against configuration.
3. 2026-11-18, user: Only use read-only access to the session store; do not restart anything.
4. 2026-11-18, user: Add the session-store dashboard to the task resources:
   `https://grafana.example.invalid/d/session-store`.
5. 2026-11-18, user: I'm logged in with my own session; reuse my token if you need it.
6. 2026-11-19, user: Was the connection pool size changed in the 2026-11-16 deploy?
   (No answer was given before the session ended.)
