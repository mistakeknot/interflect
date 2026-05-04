# Interflect

Retrospective compounding plugin/lane — 0 skills, 3 commands, 0 agents, 0 hooks,
0 MCP servers.

## Overview

Interflect reads bounded session lesson candidates and emits reviewable promotion
proposals. v0 is deliberately conservative: no automatic memory, canon, skill,
Beads, or routing mutation.

## Quick Commands

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
  --decision accepted \
  --final-target repo_doctrine \
  --rationale "Source supports the target."
PYTHONPATH=src python3 -m interflect.cli apply \
  --store /tmp/interflect-proposals.jsonl \
  --proposal-id <reviewed-idempotency-key> \
  --artifact-dir /tmp/interflect-apply-drafts
python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))"
```

## Key files

- `src/interflect/sources.py` — deterministic source adapters for session-search/CASS-style summaries.
- `src/interflect/taxonomy.py` — deterministic v0 promotion taxonomy.
- `src/interflect/proposals.py` — proposal model, idempotency, JSONL queue, review cards.
- `src/interflect/appliers.py` — review-gated dry-run apply artifacts; no target mutation.
- `src/interflect/cli.py` — manual bounded extract/analyze/review/apply commands.
- `commands/interflect.md` — Claude command guidance for proposal-only analysis.
- `commands/interflect-review.md` — review boundary guidance.
- `commands/interflect-apply.md` — reviewed safe-applier draft guidance.
- `tests/fixtures/lessons.jsonl` — 27 deterministic taxonomy examples, including real-session dogfood regressions.
- `tests/fixtures/session_summaries.jsonl` — session-search-style source adapter examples.

## Design decisions

- Namespace: `interflect:`.
- Proposal queue is JSONL in v0.
- Idempotency key: `(source_session, normalized_claim, target)`.
- Classification is deterministic lexical rules until enough reviewed proposal data
  exists to justify a learned/model-assisted layer.
- Apply paths are review-gated draft emitters only: Beads drafts include duplicate
  candidates, skill/doc paths emit patch artifacts, memory/routing emit explicit-
  approval stubs with rollback text.
