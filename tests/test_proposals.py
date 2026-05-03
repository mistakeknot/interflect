import json
from pathlib import Path

from interflect.proposals import ProposalQueue, LessonCandidate, render_review_cards
from interflect.taxonomy import PromotionTarget


def test_proposal_queue_deduplicates_by_session_claim_and_target(tmp_path):
    store = tmp_path / "proposals.jsonl"
    queue = ProposalQueue(store)
    candidate = LessonCandidate(
        source_session="sess-001",
        source_handle="discord:test",
        source_snippet="mk: wait i thought we're doing interflect",
        claim="Interflect is the active project identity, not Interspect.",
    )

    first = queue.add(candidate)
    second = queue.add(candidate)

    assert first.idempotency_key == second.idempotency_key
    assert len(queue.load()) == 1
    assert queue.load()[0].target == PromotionTarget.MEMORY


def test_review_cards_are_reviewable_and_do_not_auto_apply(tmp_path):
    store = tmp_path / "proposals.jsonl"
    queue = ProposalQueue(store)
    queue.add(LessonCandidate(
        source_session="sess-002",
        source_handle="discord:workflow",
        source_snippet="please don't silently rewrite canon from these lessons",
        claim="Interflect proposals must be reviewable before canon mutation.",
    ))

    cards = render_review_cards(queue.load())

    assert "Interflect proposal" in cards
    assert "Target: repo_doctrine" in cards
    assert "Status: proposed" in cards
    assert "No automatic mutation has been applied" in cards
