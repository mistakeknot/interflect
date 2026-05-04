# Interflect

Interflect is the retrospective-compounding plugin/lane for Sylveste and the
Interverse. It mines prior sessions for lessons and emits **reviewable promotion
proposals** to memory, skills, repo doctrine, Beads, or routing overlays.

Interflect is distinct from Interspect:

- **Interflect**: session lesson extraction and promotion proposals.
- **Interspect**: agent performance profiling, routing overrides, and canary
  monitoring.

## v0 posture

v0 is proposal-first. Analysis does not silently mutate memory, canon, skills,
Beads, or routing overlays. The only apply path emits reviewed dry-run artifacts
or explicit-approval stubs; it does not perform target mutations.

## Quick start

```bash
python3 -m pytest tests -q
PYTHONPATH=src python3 -m interflect.cli extract \
  --session-jsonl tests/fixtures/session_summaries.jsonl \
  --output-jsonl /tmp/interflect-candidates.jsonl
PYTHONPATH=src python3 -m interflect.cli analyze \
  --input-jsonl tests/fixtures/lessons.jsonl \
  --store /tmp/interflect-proposals.jsonl \
  --cards
PYTHONPATH=src python3 -m interflect.cli review \
  --store /tmp/interflect-proposals.jsonl \
  --proposal-id <idempotency-key> \
  --decision reclassified \
  --final-target skill_patch \
  --rationale "Reusable procedure, not routing evidence."
PYTHONPATH=src python3 -m interflect.cli apply \
  --store /tmp/interflect-proposals.jsonl \
  --proposal-id <reviewed-idempotency-key> \
  --artifact-dir /tmp/interflect-apply-drafts \
  --existing-beads-jsonl /home/mk/projects/Sylveste/.beads/issues.jsonl
```

## Promotion taxonomy

| Target | Purpose |
|---|---|
| `memory` | Stable cross-session user/project identity facts |
| `skill_patch` | Reusable procedures, pitfalls, or command patterns |
| `repo_doctrine` | Project-local canon, boundaries, or operating rules |
| `beads_followup` | Implementation/cleanup/review work to track |
| `routing_signal` | Model/tool/body routing evidence for Interspect or overlays |
| `runtime_only` | Transient state that should not be promoted |

## Source PRD

The initial PRD lives in Sylveste:

`docs/prds/2026-05-03-interflect-retrospective-compounding.md`
