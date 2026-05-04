import json

import pytest

from interflect.appliers import ApplyRefusal, apply_reviewed_proposal, find_beads_duplicates, require_applyable_review
from interflect.proposals import LessonCandidate, ProposalQueue
from interflect.taxonomy import PromotionTarget


def _reviewed(queue: ProposalQueue, candidate: LessonCandidate, *, decision="accepted", final_target=None):
    proposal = queue.add(candidate)
    return queue.record_review(
        proposal.idempotency_key,
        decision=decision,
        final_target=final_target,
        rationale="source supports this promotion",
        reviewed_at="2026-05-04T15:10:00Z",
    )


def test_apply_refuses_unreviewed_rejected_and_runtime_only_proposals(tmp_path):
    queue = ProposalQueue(tmp_path / "proposals.jsonl")
    unreviewed = queue.add(LessonCandidate(
        source_session="sess-followup",
        source_handle="session:todo",
        source_snippet="create a follow-up bead",
        claim="Create a Beads follow-up for Interflect safe applier UX.",
    ))

    with pytest.raises(ApplyRefusal, match="reviewed"):
        require_applyable_review(unreviewed)

    rejected = queue.record_review(unreviewed.idempotency_key, decision="rejected", rationale="not durable")
    with pytest.raises(ApplyRefusal, match="accepted or reclassified"):
        require_applyable_review(rejected)

    runtime = _reviewed(queue, LessonCandidate(
        source_session="sess-runtime",
        source_handle="runtime:port",
        source_snippet="port 9119 is listening right now",
        claim="Port 9119 was listening during this session.",
    ))
    with pytest.raises(ApplyRefusal, match="runtime_only"):
        require_applyable_review(runtime)


def test_beads_applier_emits_dry_run_draft_with_duplicate_candidates(tmp_path):
    queue = ProposalQueue(tmp_path / "proposals.jsonl")
    proposal = _reviewed(queue, LessonCandidate(
        source_session="sess-followup",
        source_handle="session:todo",
        source_snippet="create a follow-up bead",
        claim="Create a Beads follow-up for Interflect safe applier UX.",
    ))
    existing = [
        {
            "id": "sylveste-dupe",
            "title": "Interflect safe applier UX follow-up",
            "description": "Draft Beads creation should search duplicates first.",
            "status": "open",
        }
    ]

    duplicates = find_beads_duplicates(proposal, existing)
    draft = apply_reviewed_proposal(proposal, artifact_dir=tmp_path / "artifacts", existing_beads=existing)

    assert duplicates and duplicates[0]["id"] == "sylveste-dupe"
    assert draft.target == PromotionTarget.BEADS_FOLLOWUP
    assert draft.mutation_applied is False
    assert draft.artifact_path.exists()
    content = draft.artifact_path.read_text()
    assert "DRY RUN" in content
    assert "sylveste-dupe" in content
    assert "bd create" in content
    assert "No Beads mutation has been applied" in content


def test_skill_and_repo_appliers_emit_patch_artifacts_without_target_writes(tmp_path):
    queue = ProposalQueue(tmp_path / "proposals.jsonl")
    skill_target = tmp_path / "SKILL.md"
    repo_target = tmp_path / "README.md"
    skill_target.write_text("# Existing skill\n")
    repo_target.write_text("# Existing doctrine\n")

    skill = _reviewed(queue, LessonCandidate(
        source_session="sess-skill",
        source_handle="session:oracle",
        source_snippet="Oracle file wrapper pitfall",
        claim="Patch Oracle review skills to avoid bare local-path references; embed prompt contents or use a wrapper.",
    ), final_target=PromotionTarget.SKILL_PATCH)
    repo = _reviewed(queue, LessonCandidate(
        source_session="sess-doc",
        source_handle="session:boundary",
        source_snippet="Interflect review-before-mutation boundary",
        claim="Interflect proposals must be reviewable before canon mutation.",
    ), final_target=PromotionTarget.REPO_DOCTRINE)

    skill_draft = apply_reviewed_proposal(skill, artifact_dir=tmp_path / "artifacts", patch_target=skill_target)
    repo_draft = apply_reviewed_proposal(repo, artifact_dir=tmp_path / "artifacts", patch_target=repo_target)

    assert skill_target.read_text() == "# Existing skill\n"
    assert repo_target.read_text() == "# Existing doctrine\n"
    assert "diff --git" in skill_draft.artifact_path.read_text()
    assert "No target file has been modified" in skill_draft.artifact_path.read_text()
    assert "diff --git" in repo_draft.artifact_path.read_text()
    assert "No target file has been modified" in repo_draft.artifact_path.read_text()


def test_memory_and_routing_appliers_are_explicit_approval_stubs_with_rollback_text(tmp_path):
    queue = ProposalQueue(tmp_path / "proposals.jsonl")
    memory = _reviewed(queue, LessonCandidate(
        source_session="sess-memory",
        source_handle="mk:preference",
        source_snippet="terse Discord please",
        claim="mk prefers terse Discord status updates.",
    ), final_target=PromotionTarget.MEMORY)
    routing = _reviewed(queue, LessonCandidate(
        source_session="sess-routing",
        source_handle="review:routing",
        source_snippet="browser QA needed",
        claim="UI visual bugs should route to browser QA when snapshots are insufficient.",
    ), final_target=PromotionTarget.ROUTING_SIGNAL)

    memory_draft = apply_reviewed_proposal(memory, artifact_dir=tmp_path / "artifacts")
    routing_draft = apply_reviewed_proposal(routing, artifact_dir=tmp_path / "artifacts")

    assert memory_draft.mutation_applied is False
    assert routing_draft.mutation_applied is False
    assert "EXPLICIT APPROVAL REQUIRED" in memory_draft.artifact_path.read_text()
    assert "Rollback" in memory_draft.artifact_path.read_text()
    assert "EXPLICIT APPROVAL REQUIRED" in routing_draft.artifact_path.read_text()
    assert "Rollback" in routing_draft.artifact_path.read_text()
