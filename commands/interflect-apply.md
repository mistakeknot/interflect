# /interflect:apply

Emit safe apply **drafts** for already-reviewed Interflect proposals.

This command is not an automatic mutation path. It turns reviewed proposals into
operator-readable artifacts: Beads draft commands, skill/doc patch drafts, or
explicit-approval stubs for memory/routing.

## Review gate

Refuse unless the proposal queue record has:

- `status: reviewed`
- `review_decision: accepted` or `review_decision: reclassified`
- `final_target` or `target` that is not `runtime_only`

Rejected, proposed, and runtime-only proposals must not create apply artifacts.

## Local CLI

```bash
interflect apply \
  --store .interflect/proposals.jsonl \
  --proposal-id <idempotency-key> \
  --artifact-dir .interflect/apply-drafts \
  --existing-beads-jsonl /path/to/issues.jsonl
```

Optional patch artifact context:

```bash
interflect apply \
  --store .interflect/proposals.jsonl \
  --proposal-id <idempotency-key> \
  --artifact-dir .interflect/apply-drafts \
  --patch-target skills/example/SKILL.md
```

## Target behavior

- `beads_followup`: search the provided Beads JSONL corpus for likely duplicates
  and emit a dry-run `bd create` draft. Do not execute it.
- `skill_patch` / `repo_doctrine`: emit patch/diff artifacts only. Do not edit
  the target file.
- `memory` / `routing_signal`: emit explicit-approval stubs with rollback text.
  Do not mutate memory or routing overlays.
- `runtime_only`: refuse.

Every artifact must say what did **not** happen. No memory, canon, skill, Beads,
or routing mutation has been applied.
