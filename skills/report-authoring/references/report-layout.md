# Investigation report layout

Assume the reader stops after the first fifth of the report. The opening section must carry
the conclusion, what to do about it, and the graphs that show it; everything else is
supporting detail a reader can reach by link.

## Opening section

ALWAYS use this order. The report opens with its title: no publication note, revision note or
navigation preamble goes above it, in the report or on a published page.

1. **Title, metadata line and current-status line.** [Token Usage](../../token-usage/SKILL.md)
   owns the metadata line.
2. **`## Key findings`, starting with a `**Bottom line.**` paragraph.** State what happened,
   what the evidence shows, what is still unproven, and the state of remediation, with
   evidence identifiers.
3. **`### Proposed remediation` table** with the columns `Remediation`, `What it addresses`
   and `Status`. Give one row per proposal, stopgaps first and labeled as stopgaps. `Status`
   says whether the item is observed, proposed, implemented or validated, and what gates it.
   Follow the table with one line stating what has and has not been changed. When the
   investigation proposes no remediation, say so in that line instead of omitting the heading.
4. **`### What the evidence shows` table** with the columns `Question`, `What the evidence
   shows` and `Status`. `Status` uses the evidence labels from the skill entrypoint (verified,
   observed, supported, candidate, unverified) and names the limit that applies.
5. **Headline graphs.** One numbered `###` subsection per key point. The heading states the
   finding. Give one takeaway paragraph, then the figure and its complete caption.
6. **Validation gate.** A `### Before <the fix> is treated as the fix` list of the checks
   that would confirm or refute the leading candidate, in dependency order.
7. **One closing paragraph** linking each supporting section.

## Supporting detail

Keep this order after the opening: the finding statement in full; mechanism and uncertainty;
each data-pattern section with its remaining graphs and tables; source analysis; next checks
and remediation detail; scope and timing; coverage and limitations; the continuation record,
resume checkpoint and dependency inventory, whose contents
[Report Continuation](../../report-continuation/SKILL.md) owns; the Evidence index; appendices;
delivery and accounting; token usage details.

## Rules

- **Nothing new in the opening.** Every sentence and table row restates a finding or proposal
  recorded in the detail, with the same evidence identifiers and the same qualification. A
  candidate stays a candidate; a correlation stays a correlation.
- **Choose the headline graphs by what they prove.** Put the graph for the cause and the
  graph for the reported symptom in the opening. A pattern whose graph stays in the detail
  gets a row in the evidence table that links to its figure.
- **A moved graph leaves a cross-reference.** The detail section that owned the graph links
  to its figure in the opening. A flapping-alert pair moves as one unit with its caption;
  [Diagramming Style](../../diagramming-style/references/flapping-alert-graphs.md) owns its
  pairing and placement.
- **Raw listings go in an appendix.** A table that lists one row per alert, pod, request or
  similar record, and runs past about eight rows, moves unchanged to an `## Appendix: <subject>`
  section after the Evidence index. The section that cites it keeps a one-sentence summary of
  what the rows show and a link to the appendix. Use an appendix link, not a Markdown footnote:
  the HTML generator and Confluence do not render footnotes. Tables that carry the argument
  (the remediation and evidence tables, short comparisons) stay where they are.
- **Captions stay complete.** To save space, display a headline graph at a smaller width.
  Never shorten its caption or change the image file.
- **Number figures in order of appearance.** When restructuring an existing report, record
  the old-to-new numbering in the continuation record.
- **Hold the opening to the first 20%.** Measure where the opening ends in each selected
  format (line position against total lines for Markdown, rendered page height for HTML, page
  count for PDF) and record the figures in the
  validation receipt. When required graphs make 20% unreachable, keep the bottom line, both
  tables and the first graph inside it and record the overage. Do not drop a required graph
  or caption to meet the number.
- **Restructuring moves text verbatim.** Limit wording changes to figure numbers,
  cross-references and the record of the restructure. Save the prior files before replacing
  them, and regenerate every selected format from the reordered source.

## Skeleton

```markdown
# <Report title>

<metadata line>

Current status: <one line>

## Key findings

**Bottom line.** <what happened; what the evidence shows; what is unproven; remediation state> [E1](…)

### Proposed remediation

| Remediation | What it addresses | Status |
|---|---|---|
| **Stopgap: <action>** | <symptom> | Observed once; does not remove the cause [E2](…) |
| **<fix>** | Candidate cause: <cause> | Proposed, not implemented; needs <gate> [E3](…) |

Nothing has been changed in production. Detail: [proposed remediation](#…).

### What the evidence shows

| Question | What the evidence shows | Status |
|---|---|---|
| What caused it? | <measured fact> [E4](…) | Verified for <scope>; not <limit> |

### 1. <Finding stated as a sentence>

<one takeaway paragraph> [E4](…)

<a id="figure-1"></a>

<figure and complete caption>

### Before <the fix> is treated as the fix

1. **<check>:** <evidence that would confirm or refute>

Everything below is supporting detail: [<section>](#…), …
```

## Checklist

- [ ] The report opens with its title; no preamble sits above it in any format or publication.
- [ ] Bottom line, remediation table, evidence table, headline graphs and validation gate
      appear in that order.
- [ ] Every opening claim and table row matches the detail in wording strength and citation.
- [ ] Each moved graph has a cross-reference in its detail section; figures are numbered in
      order of appearance.
- [ ] Raw row listings sit in an appendix, each with a summary and link where it is cited.
- [ ] The opening's end position is measured and recorded for each selected format.
