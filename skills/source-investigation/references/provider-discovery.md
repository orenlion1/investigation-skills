# Discover source through the supplied VCS

## Resolve and search

A task repository identifies both a starting repository and a provider context. Resolve its
VCS provider, host and authorized account/workspace through the approved tooling and existing
access. A Bitbucket repository therefore supplies a Bitbucket search context even if it holds
only alert definitions and cannot explain the application behavior. Do not require a second
repository resource or renewed approval for discovery covered by the root policy grant.

Keep separate scopes for distinct hosts/accounts/workspaces. A provider name alone does not
authorize searching every organization on that provider. Preserve explicit repository-only or
other narrower user limits; if account/workspace identity cannot be resolved, report that gap
instead of guessing. Discovery is read-only and does not authorize source changes or publication.

Use observed service/workload names, profile or stack symbols, package names, log components,
dependencies and deployment metadata to search repository metadata and available code indexes.
Discover supported search operations first. If code search is unavailable, inspect bounded
candidate listings and directory/source reads through the same approved provider tooling;
disclose caps, pagination and unavailable coverage. Do not change providers or access methods
after a failure without authorization.

Inspect likely application, shared-library, caller and configuration repositories. Verify each
candidate against the observed symbols and execution path rather than accepting a name match.
Resolve its revision, trace the relevant implementation and consumers, and check deployment
provenance under the main skill. Continue relevant dependency tracing within the resolved scope;
do not indiscriminately read every accessible repository.

## Retain evidence

Extend the repository ledger with discovered candidates, why each was selected or excluded,
search queries and bounds, read outcomes and inspected revisions. Coordinate discovered
dependencies with the existing inspection owner through the parent scheduling workflow;
discovering a repository neither edits task Resources nor creates a duplicate inspection unit.
Pin material findings to source and distinguish inspected code from verified deployed behavior.

An unrelated seed repository, an empty capped listing, a missing search tool or an access denial
is not proof that relevant source does not exist. Before delivery, identify what source was
searched and inspected, and any unresolved discovery or deployment gap. Never present a
telemetry-only explanation as completed source tracing when this required step was omitted.

## Sanitized example: CPU flapping and archived reads

A task names an alert-configuration repository in Bitbucket. Runtime evidence shows recurring
CPU pressure in an application, and a later lead mentions historical event replay and recovery
after a rolling restart. The supplied configuration repository is not the application's source.

Use its verified Bitbucket workspace to discover the application repository and relevant cache
or storage dependencies. Correlate observed profiling symbols with archived-file loading and
event parsing; inspect the request path, queued versus active job deduplication, retries and
parser progress. This should happen without waiting for the user to supply the application
repository. Code may support duplicate replay work as a candidate mechanism, while the actual
incident requests, deployed revision, traffic change and deadlock remain unverified.

This example deliberately omits organization names, repository identifiers, source paths,
symbols, incident dates and URLs. Apply the same sanitization to reusable examples and evals;
retain precise private citations only in the authorized investigation's evidence artifacts.
