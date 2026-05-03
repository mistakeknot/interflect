# interflect — Agent Guide

Retrospective compounding for reviewable lesson promotion proposals.

## Canonical References

1. `PHILOSOPHY.md` — why Interflect exists and where it sits in OODARC.
2. `CLAUDE.md` — implementation details and validation commands.
3. Sylveste PRD: `docs/prds/2026-05-03-interflect-retrospective-compounding.md`.

## Quick Reference

| Item | Value |
|---|---|
| Repo | `https://github.com/mistakeknot/interflect` |
| Namespace | `interflect:` |
| Manifest | `.claude-plugin/plugin.json` |
| Components | 0 skills, 2 commands, 0 agents, 0 hooks, 0 MCP servers |
| License | MIT |

## Scope

Interflect extracts and classifies session lessons, then emits proposals. It does
not silently mutate canon.

## Boundary

- Interflect owns retrospective lesson promotion proposals.
- Interspect owns performance profiling and routing optimization.
- Routing-signal proposals may feed Interspect after review.

## Validation

```bash
python3 -m pytest tests -q
python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))"
```

## Development rules

- Keep v0 proposal-only.
- Preserve source handles and snippets on every proposal.
- Deduplicate by idempotency key before writing.
- Add tests for every taxonomy or proposal behavior change.
