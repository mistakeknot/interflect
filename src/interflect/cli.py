from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from .proposals import ProposalQueue, candidates_from_jsonl, render_review_cards
from .taxonomy import PromotionTarget


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="interflect", description="Reviewable retrospective-compounding proposals")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Analyze bounded lesson candidates and update proposal queue")
    analyze.add_argument("--input-jsonl", required=True, help="JSONL lesson candidates with source_session/source_handle/claim")
    analyze.add_argument("--store", default=".interflect/proposals.jsonl", help="Proposal queue JSONL path")
    analyze.add_argument("--session", action="append", default=[], help="Explicit session handle included in this bounded run")
    analyze.add_argument("--recent", default=None, help="Bounded recent window label, e.g. 7d; metadata only in v0")
    analyze.add_argument("--cards", action="store_true", help="Render review cards instead of JSON summary")

    review = sub.add_parser("review", help="Record a human review outcome for an existing proposal")
    review.add_argument("--store", default=".interflect/proposals.jsonl", help="Proposal queue JSONL path")
    review.add_argument("--proposal-id", required=True, help="Proposal idempotency key to update")
    review.add_argument("--decision", required=True, choices=["accepted", "reclassified", "rejected"], help="Human review decision")
    review.add_argument("--final-target", choices=[target.value for target in PromotionTarget], help="Reviewed final target")
    review.add_argument("--rationale", default="", help="Human review rationale")
    review.add_argument("--reviewed-at", default=None, help="ISO timestamp for deterministic/imported reviews")
    return parser


def analyze(args: argparse.Namespace) -> int:
    queue = ProposalQueue(Path(args.store))
    touched = []
    session_filter = set(args.session)
    for candidate in candidates_from_jsonl(args.input_jsonl):
        if session_filter and candidate.source_session not in session_filter:
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


def review(args: argparse.Namespace) -> int:
    reviewed_at = args.reviewed_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    queue = ProposalQueue(Path(args.store))
    proposal = queue.record_review(
        args.proposal_id,
        decision=args.decision,
        final_target=args.final_target,
        rationale=args.rationale,
        reviewed_at=reviewed_at,
    )
    print(json.dumps(proposal.to_json(), ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return analyze(args)
    if args.command == "review":
        return review(args)
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
