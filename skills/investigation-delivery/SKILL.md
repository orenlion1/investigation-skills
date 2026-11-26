---
name: investigation-delivery
description: "Render local HTML investigation reports from saved canonical findings, coordinate timing and selected outputs, and verify handoff. Use when generating report exports, applying shared delivery checkpoints, or resolving delivery prerequisites through Profile Manager."
---

# Investigation Delivery

## Overview

Own the shared investigation timing and delivery workflow, independently of task editing.
Read the [delivery contract](references/delivery-contract.md) before setup or final handoff.
It contains the timing helper interface, checkpoint, source identity, output orchestration,
and verification rules. Use [HTML generation](references/html-generation.md) for the local renderer
and export checks. Provider access and mutation/publication authorization stay with
those workflows and the caller.

[Profile Manager](../profile-manager/SKILL.md) owns effective format settings and their
validation; read its contract and use its helper rather than restating defaults or precedence.
[Report Authoring](../report-authoring/SKILL.md) owns evidence and report QA,
[Report Continuation](../report-continuation/SKILL.md) owns canonical identity and context,
and [Token Usage](../token-usage/SKILL.md) owns accounting. The editor barrier stays with
[Open/Edit/Close/Execute](../open-edit-close-execute/SKILL.md).

## When to Use

- Coordinate the shared checkpoint for a direct or editor-started investigation.
- Select delivery tooling from owner-resolved settings or verify a final handoff.

## Common Rationalizations

| Rationalization | Correction |
| --- | --- |
| "The delivery guide can carry convenient defaults." | Read settings through Profile Manager. |
| "A checkpoint ends the investigation." | Follow the contract's soft-checkpoint procedure and retain its gates. |

## Red Flags

- Treating an output preference as permission to publish or refresh evidence.
- Reporting complete delivery before its applicable checks finish.

## Verification

- Read back the effective output settings through their owner before dependency setup.
- Preserve the root observation boundary, waits, and checkpoint across continuations.
- Verify each selected output and identify unavailable evidence or QA separately.
- Reuse historical evidence/accounting boundaries for delivery of existing findings.
