from __future__ import annotations

import argparse
import json
from pathlib import Path

from .proposals import ProposalQueue, candidates_from_jsonl, render_review_cards


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="interflect", description="Reviewable retrospective-compounding proposals")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Analyze bounded lesson candidates and update proposal queue")
    analyze.add_argument("--input-jsonl", required=True, help="JSONL lesson candidates with source_session/source_handle/claim")
    analyze.add_argument("--store", default=".interflect/proposals.jsonl", help="Proposal queue JSONL path")
    analyze.add_argument("--session", action="append", default=[], help="Explicit session handle included in this bounded run")
    analyze.add_argument("--recent", default=None, help="Bounded recent window label, e.g. 7d; metadata only in v0")
    analyze.add_argument("--cards", action="store_true", help="Render review cards instead of JSON summary")
    return parser


def analyze(args: argparse.Namespace) -> int:
    queue = ProposalQueue(Path(args.store))
    touched = []
    for candidate in candidates_from_jsonl(args.input_jsonl):
        if args.session and candidate.source_session not in set(args.session):
            continue
        touched.append(queue.add(candidate))

    if args.cards:
        print(render_review_cards(touched))
    else:
        print(json.dumps({
            "store": args.store,
            "proposals_seen": len(touched),
            "sessions": args.session,
            "recent": args.recent,
        }, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return analyze(args)
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
