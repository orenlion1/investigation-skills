---
name: investigation-reasoning
description: "Choose and revise evidence questions while executing a root-cause investigation. Use when turning observations or user follow-ups into testable hypotheses, comparing explanations, or deciding the next bounded evidence check across sources."
---

# Investigation Reasoning

## Overview

Own the question-and-evidence loop during investigation execution. Read
[the questioning workflow](references/questioning-loop.md) before choosing the next check.
Use it after material answers and corrections, not just during the initial plan.

## When to Use

- Choose the next evidence check during a root-cause investigation.
- Convert a user challenge or new observation into a testable explanation.
- Reconsider a proposed mechanism when comparison evidence contradicts it.

## Boundaries

This skill selects the question, competing explanations and distinguishing evidence. It does
not collect provider data, schedule inspection units, trace code, render reports or change
resources. Use the configured provider owners for reads,
[Per-Store Fan-Out](../per-store-fan-out/SKILL.md) for inspection scheduling,
[Source Investigation](../source-investigation/SKILL.md) for code and deployed-revision analysis,
[Report Authoring](../report-authoring/SKILL.md) for evidence/graph coverage, and
[Report Continuation](../report-continuation/SKILL.md) for the continuing question/answer record.
Follow those owners rather than copying their procedures here.

Exact queries, inventory requests, setup-only work and publication-only work retain their
requested scope; they do not automatically become root-cause investigations. Reuse the saved
scope, evidence and root delivery budget. New questions create no authority for wider reads,
additional paid prompts, production changes, messages or publication.

## Common Rationalizations

- "More copies of the symptom will settle the cause." Choose evidence that distinguishes
  the candidate from its strongest alternative.
- "The user named the mechanism." Treat it as a hypothesis with observable predictions.

## Red Flags

- Calling a hotspot a causal explanation without its triggering conditions.
- Broad discovery replacing a precise unresolved question.
- A scope expansion or provider procedure introduced by the reasoning layer.

## Verification

- Each material open question has an observation, candidate, alternative and discriminating
  evidence request, or a concrete reason it cannot be checked.
- Answers update the next question and the continuing evidence record; a repeated symptom
  or unavailable check is not silently promoted into causal proof.
- Collection, code, report, visual and continuation work stays with its named owner.
