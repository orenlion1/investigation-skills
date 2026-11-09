# Flapping Alerts: Daily Peaks and Observed Intervals

This reference owns the visual specification of the required graph pair for flapping or
recurring alert investigations: **Daily peaks and alert outcomes** and **Observed Pending and
Alerting intervals**. The [report-evidence](../../report-evidence/SKILL.md) skill owns the
requirement that the pair exists and matches the report's evidence; this reference owns how
the pair looks and renders. These are complementary views of the same evidence: the daily
summary compares peak magnitude and outcome; the interval view explains when states began,
how long they lasted, and recovery.

## Daily peaks and alert outcomes

- Plot one observed daily peak per date for the relevant metric, using UTC dates on the
  horizontal axis and the metric's actual units on the vertical axis. For count-based
  alerts, use the corresponding daily event count or peak count and state the aggregation.
  Show the alert threshold as a dashed horizontal line when the rule has a numeric threshold.
- Encode each day's observed outcome with both shape and color: circles for **Pending only**
  and squares for **Reached Alerting**, with an explicit legend. Derive outcomes from saved
  alert-state history, independently of the daily peak; an above-threshold peak does not
  establish that an alert fired. Represent other observed outcomes separately and identify
  unavailable state history rather than classifying it as Pending only or Normal.
- Preserve missing days as gaps. Identify partial days, exact coverage/cutoff, timezone,
  source resolution and peak aggregation in the adjacent caption; do not imply full-day
  coverage or threshold residence from a peak. Cite metric and alert-history evidence.

## Observed Pending and Alerting intervals

- Draw the interval view from observed state transitions, with a row for each date and
  clearly labeled clock time or minutes from a stated reference time. Show Pending and
  Alerting intervals and their observed recovery boundaries; preserve missing history or
  unresolved ends rather than inventing interval limits.

## Pairing and placement

- Present the two graphs as one cohesive pair in both Markdown and PDF, preferably stacked
  with the daily summary above the intervals, or side by side when labels remain readable.
  Use the same resource, evidence window, timezone, chronological date order, and consistent
  state colors across both views. Put a short shared takeaway and linked evidence immediately
  beside the pair, explaining how peak magnitude relates to state duration and firing outcome.
- Keep both views and their shared takeaway together on one PDF page when they fit readably;
  use a dedicated page or reflow before separating them. If separation is unavoidable, use
  consecutive pages with explicit cross-references and no intervening content. Never insert
  a table, long prose, unrelated graph, or section break between the two views. Verify their
  actual rendered placement, not only their source order.
- Keep the section heading and its first graph together in PDF when they fit on a page; do
  not leave a pattern section with only a table or prose while its graph appears on a later
  page without an explicit cross-reference.
- Full-window time series, daily-profile overlays and tables may supplement this required
  pair but never replace either view. Apply the guide's required light/dark variants and
  preserve the same pairing, captions and takeaway in every delivered format.
- Label axes, units, resource identities, exact time window and timezone, resolution, and
  aggregation in the graph or adjacent caption, per the main
  [Diagramming Style Guide](diagramming-style.md).
