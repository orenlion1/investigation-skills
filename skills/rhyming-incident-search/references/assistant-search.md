# Assistant matching requests

Only `grafana-assistant-search` permits a new scoped billable Assistant prompt. History-only
endpoints retain their list/get restrictions. This reference owns prompt preparation and execution
accounting; delegation remains owned by the [shared contract](../../per-store-fan-out/references/delegation-contract.md).

## Prepare before any initial prompt

The parent resolves every endpoint and both windows before launching either historical or current
Assistant work. Run the pure standard-library preparation helper (Python 3.9+ for IANA timezone
validation) with sanitized JSON on stdin:

```sh
python3 -B skills/rhyming-incident-search/scripts/prepare_assistant_search.py < resolved-input.json
```

Use the validated endpoint read from Profile Manager, not a second `.env` parser. The helper imports
that complete sibling package and validates endpoints again. Input shape:

```json
{
  "endpoints": [{"id":"match","kind":"grafana-assistant-search","target":"service-a","context":"ops"}],
  "assistant_enabled": true,
  "shared": {
    "incident": "incident-example elevated latency",
    "symptoms": "HTTP 503",
    "services_environment": "service-a production",
    "incident_window": {"start":"2026-11-09T12:00:00Z","end":"2026-11-09T13:00:00Z","timezone":"UTC"},
    "historical_window": {"start":"2026-11-02T12:00:00Z","end":"2026-11-09T12:00:00Z","timezone":"UTC"},
    "matching_criteria": "symptoms, components, mechanisms, mitigations",
    "permitted_terms_redactions": "service-a only; omit personal data"
  },
  "existing_branches": []
}
```

A prospective current-investigation Assistant branch is an object with `reference`, `context`,
`scope`, `shared`, `prompt_sent` (boolean) and `initial_prompt`. Pass its exact resolved incident
block as `shared`, its exact permitted scope as `scope`, and its original request as `initial_prompt`.
Do not mark an already submitted prompt unsent. Resolve ambiguous branch ownership before execution.
The helper produces arguments and owner/consumer references only: it sends nothing, authenticates
nowhere, and allocates no agents. Prepared output is sensitive local evidence, never committed.

The prompt passes incident identity, symptoms, services/environment, both windows/timezones,
permitted terms/redactions, configured endpoint scope, matching criteria, read-only constraints and
evidence requirements. It asks for candidate identifiers, source links, timestamps/versions,
matching facts, contradictions, mechanisms/mitigations and limitations. Similarities remain hypotheses.
Inspect the sanitized prompt for scope fidelity before execution. Check executing-host help and
apply gcx-cli's setup/refresh/authentication before operational reads.

## One execution owner, separate endpoint children

Consume the helper's `endpoints` and `executions` together. These are preparation records, not a
launch manifest and not evidence of execution. Match contexts, scope strings and the complete shared
block exactly; equivalent-looking phrases do not justify broadening scope or guessing equivalence.
Every configured endpoint retains its own child and manifest row. History-only rows retain their
existing behavior. A configured disabled or failed-to-launch row remains present under the contract.

For each compatible group, the existing unsent Assistant branch owns the combined initial prompt.
It includes its original investigation request and the matching request before submission. Without
such a branch, one designated prompt endpoint child is the owner and other endpoint children are
consumers. Prepare owners before consumers can exhaust capacity waiting for an unscheduled owner;
independent history searches do not wait for Assistant results. Submit independent endpoint work
under the existing rhyming scheduling contract. Consumers inspect the shared retained response for
their endpoint; they must never send another prompt or copy the owner's child identity.

The owner executes the prepared `arguments` array using a structured process call, never shell
joining. Its effective command is:

```sh
gcx assistant prompt "$RHYMING_REQUEST" --context "$GCX_CONTEXT" --json --no-stream --timeout 300
```

Use one fresh conversation per new execution. No arbitrary `--continue` or `--context-id`. The prompt
has its own 300-second wait; history/detail/verification reads keep their 60-second limit, the
3-read/20-candidate endpoint budgets and 2 follow-up rounds. Count prompt submission against each
participant's query budget, but count the shared billable request only once across the run.
Do not imply that Assistant's internal search is bounded by CLI read/candidate limits: pass limits
in the request, cap returned candidates and disclose any unobservable internal coverage.

Before submission, retain a local execution receipt with the prepared reference, owner reference,
participating endpoint IDs, exact resolved context/scope/shared block and prompt, and pending status.
Bind it to the actual owner child/branch record. After submission, append observed submission time,
actual prompt count, response/conversation identifiers when available, response/reference paths,
provider source references and limitations. Never turn a deterministic preparation reference into a
claimed conversation or child ID. Consumers reference the same receipt; their own query/candidate
and parent-verification counts remain separate. The parent verifies inclusion against the retained
initial prompt, links both manifests and rejects missing, extra or duplicate endpoint results.

An already-sent compatible branch makes initial-prompt reuse unavailable. Record that endpoint's
limitation and send no second prompt automatically. Do not attach a follow-up and claim initial
inclusion. A failed owner makes consumers unavailable for that execution while other endpoints
continue. Timeout or uncertain submission means uncertain outcome; inspect the existing receipt and
conversation within authorized bounds before any expressly authorized retry. Never blindly resubmit.

## Disabled and evidence outcomes

`Grafana Assistant: disabled` or a user disable instruction means `assistant_enabled: false` and
zero prompt submissions, including combined prompts. Record configured disabled endpoints/branches
as limitations, not failures; continue permitted history searches. Parent fan-out disablement still
controls nested delegation independently.

Malformed JSON, denial, timeout, absent identifiers and inaccessible references are explicit gaps.
Preserve sanitized response, identifiers, references and limitations; do not invent absent fields or
switch provider/context. Missing or out-of-window candidate timestamps cannot establish historical
matches. Child output remains leads. The parent verifies every material match directly against
retrievable source evidence within the endpoint read budget, recording reference and observation
time. Distinguish evidence-backed relationship, hypothesis, no matches within searched scope and
unavailable. No shared-root-cause claim follows merely from similarity or Assistant confidence.
