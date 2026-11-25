# Cache eviction storm, follow-up investigation

Synthetic fixture, not production findings. Report formats: Markdown only.

## Finding

Evictions rose when the memory limit was reached. [E1](#E1)

## Related work

The earlier storm is tracked as [incident 1042](https://tracker.example.invalid/incidents/1042) and was analysed in the
[prior investigation](REPORT-cache-evictions-prior.md), whose evidence [E2](REPORT-cache-evictions-prior.md#E2) and
[E4](REPORT-cache-evictions-prior.md#E4) are reused here.

## Historical reconciliation

The pattern matches incident 1042. The prior report's E2 shows the same counter shape, and its E4 shows the same memory limit.
A second incident, incident 1077, was mentioned in chat; no record of it was available to inspect.

## Evidence index

Source: synthetic cache cluster, samples 02:00-03:00 UTC; read-only; no configuration change tested.

- <a id="E1"></a>E1 - Eviction counter samples, this investigation.
- <a id="E5"></a>E5 - Comparison with the prior report's E2 and with incident 1042.
