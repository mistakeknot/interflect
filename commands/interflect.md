# /interflect

Proposal-only retrospective compounding. No automatic mutation is allowed.

Use this command when the operator asks to mine prior sessions, CASS summaries,
Beads notes, or repo handoffs for lessons that should be reviewed for promotion.

## Behavior

1. Identify the bounded source window:
   - explicit session handles, if provided;
   - otherwise a small recent window named by the operator.
2. Extract candidate lessons with source handles and short snippets.
3. Classify each candidate into Interflect's promotion taxonomy:
   - `memory`
   - `skill_patch`
   - `repo_doctrine`
   - `beads_followup`
   - `routing_signal`
   - `runtime_only`
4. Emit review cards and/or JSONL proposals.
5. Stop. Do not apply memory, skill, canon, Beads, or routing mutations. If the
   operator explicitly invokes a reviewed apply path, emit only dry-run artifacts
   or explicit-approval stubs.

## Local CLI

Extract candidates from session-search-style summaries:

```bash
interflect extract \
  --session-jsonl tests/fixtures/session_summaries.jsonl \
  --output-jsonl .interflect/candidates.jsonl
```

Analyze explicit candidates:

```bash
interflect analyze \
  --input-jsonl tests/fixtures/lessons.jsonl \
  --store .interflect/proposals.jsonl \
  --cards
```

Emit a reviewed dry-run apply artifact:

```bash
interflect apply \
  --store .interflect/proposals.jsonl \
  --proposal-id <reviewed-idempotency-key> \
  --artifact-dir .interflect/apply-drafts \
  --existing-beads-jsonl /path/to/issues.jsonl
```

## Output contract

Every proposal must include:

- source session / handle
- source snippet
- normalized claim
- target substrate
- confidence
- rationale
- idempotency key
- status `proposed`, then review state (`review_decision`, `final_target`, `review_rationale`, `reviewed_at`) once reviewed

No automatic mutation has been applied.
