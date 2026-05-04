from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from .appliers import ApplyRefusal, apply_reviewed_proposal, load_jsonl_records
from .proposals import ProposalQueue, candidates_from_jsonl, render_review_cards
from .sources import candidates_from_session_summaries
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

    extract = sub.add_parser("extract", help="Extract lesson candidates from session_search/CASS-style summaries")
    extract.add_argument("--session-jsonl", required=True, help="JSONL session summary export")
    extract.add_argument("--output-jsonl", help="Write extracted LessonCandidate JSONL instead of stdout")
    extract.add_argument("--store", help="Optional proposal queue path; when set, extracted candidates are analyzed into proposals")
    extract.add_argument("--session", action="append", default=[], help="Filter to explicit source_session values")
    extract.add_argument("--cards", action="store_true", help="With --store, render review cards for touched proposals")

    apply_cmd = sub.add_parser("apply", help="Emit reviewed safe-applier draft artifacts without target mutation")
    apply_cmd.add_argument("--store", default=".interflect/proposals.jsonl", help="Proposal queue JSONL path")
    apply_cmd.add_argument("--proposal-id", required=True, help="Reviewed proposal idempotency key to draft")
    apply_cmd.add_argument("--artifact-dir", default=".interflect/apply-drafts", help="Directory for dry-run artifacts")
    apply_cmd.add_argument("--existing-beads-jsonl", help="Optional JSONL Beads export/search corpus for duplicate detection")
    apply_cmd.add_argument("--patch-target", help="Optional intended skill/doc file path for patch artifact context")
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


def extract(args: argparse.Namespace) -> int:
    session_filter = set(args.session)
    candidates = [
        candidate for candidate in candidates_from_session_summaries(args.session_jsonl)
        if not session_filter or candidate.source_session in session_filter
    ]

    if args.store:
        queue = ProposalQueue(Path(args.store))
        touched = [queue.add(candidate) for candidate in candidates]
        if args.cards:
            print(render_review_cards(touched))
        else:
            print(json.dumps({
                "store": args.store,
                "candidates_seen": len(candidates),
                "proposals_seen": len(touched),
                "sessions": args.session,
            }, indent=2))
        return 0

    lines = [json.dumps(candidate.__dict__, ensure_ascii=False, separators=(",", ":")) for candidate in candidates]
    output = "\n".join(lines) + ("\n" if lines else "")
    if args.output_jsonl:
        output_path = Path(args.output_jsonl)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output)
    else:
        print(output, end="")
    return 0


def apply(args: argparse.Namespace) -> int:
    queue = ProposalQueue(Path(args.store))
    proposals = {proposal.idempotency_key: proposal for proposal in queue.load()}
    proposal = proposals.get(args.proposal_id)
    if proposal is None:
        print(f"proposal not found: {args.proposal_id}", file=sys.stderr)
        return 1

    existing_beads = load_jsonl_records(args.existing_beads_jsonl) if args.existing_beads_jsonl else []
    try:
        draft = apply_reviewed_proposal(
            proposal,
            artifact_dir=args.artifact_dir,
            existing_beads=existing_beads,
            patch_target=args.patch_target,
        )
    except ApplyRefusal as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(draft.to_json(), ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return analyze(args)
    if args.command == "review":
        return review(args)
    if args.command == "extract":
        return extract(args)
    if args.command == "apply":
        return apply(args)
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
