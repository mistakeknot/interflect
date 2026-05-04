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
    assert queue.load()[0].target == PromotionTarget.REPO_DOCTRINE


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


def test_queue_records_review_outcome_as_first_class_state(tmp_path):
    store = tmp_path / "proposals.jsonl"
    queue = ProposalQueue(store)
    proposal = queue.add(LessonCandidate(
        source_session="sess-003",
        source_handle="discord:oracle",
        source_snippet="Oracle review skill needs file wrapper guidance.",
        claim="Patch Oracle review skills to avoid bare local-path references; embed prompt contents or use a wrapper that passes files correctly.",
    ))

    reviewed = queue.record_review(
        proposal.idempotency_key,
        decision="reclassified",
        final_target=PromotionTarget.SKILL_PATCH,
        rationale="Reusable Oracle review procedure pitfall.",
        reviewed_at="2026-05-04T08:40:00Z",
    )

    assert reviewed.status == "reviewed"
    assert reviewed.review_decision == "reclassified"
    assert reviewed.final_target == PromotionTarget.SKILL_PATCH
    assert reviewed.review_rationale == "Reusable Oracle review procedure pitfall."
    assert reviewed.reviewed_at == "2026-05-04T08:40:00Z"

    reloaded = queue.load()[0]
    assert reloaded.idempotency_key == proposal.idempotency_key
    assert reloaded.review_decision == "reclassified"
    assert reloaded.final_target == PromotionTarget.SKILL_PATCH

    raw = json.loads(store.read_text().strip())
    assert raw["review_decision"] == "reclassified"
    assert raw["final_target"] == "skill_patch"
    assert raw["review_rationale"] == "Reusable Oracle review procedure pitfall."
