# Synthetic investigation exercise

No live Grafana, AWS, Slack or VCS access is authorized. `provider.py` is the only provider interface; its responses represent read-only integration results. Use `python3 provider.py catalog` and `python3 provider.py read KEY --context fixture-eu --profile fixture-eu --region eu-central-1`. Reads save exact responses and arguments in receipts/. Do not read data/ directly as a substitute for provider calls. No model prompt, credential, setup change or external message is needed.

Use returned facts, not labels, to distinguish source configuration from Kubernetes changes. Saved profile stack arrays are native-shaped synthetic Pyroscope input. A missing profile is not zero. Earlier behavior may recur; ordinary parser presence need not be the incident workload. `saved-handoff.json` is the frozen collection output for delivery-only prompts; those prompts require no provider calls.

For delivery, preserve the canonical HTML path. Use the generic plot.py helper or other standard plotting tools, with reproducible data/source, matching light/dark SVG+PNG assets and readable annotations; actual profile stacks also need representative flame graphs via the loaded Diagramming Style owner. The generic plot helper accepts a JSON object with views; each view has title, ylabel, points [{time,value}], and events [{time,label}]. Missing values are null, not zero. The helper intentionally does not choose evidence, semantics, views or labels for you.

All workload, namespace, account/profile, context, channel and source identities are fabricated. The demo namespace, worker names, June 14 example timeline, reserved example domains and repeated-a commit are synthetic; no production identifiers or raw organizational payloads are required. Vendor and standard API names remain to exercise the integration semantics.

The operator provisions skill_evals/requirements.txt before the offline run; python3 has the pinned plotting, HTML and SVG rasterization libraries on PATH. Use those installed tools without package downloads or user environment changes during the exercise.
