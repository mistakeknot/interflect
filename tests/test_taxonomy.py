import json
from collections import Counter
from pathlib import Path

from interflect.taxonomy import PromotionTarget, classify_lesson


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "lessons.jsonl"


def load_fixtures():
    return [json.loads(line) for line in FIXTURE_PATH.read_text().splitlines() if line.strip()]


def test_fixture_lessons_classify_deterministically_across_all_targets():
    fixtures = load_fixtures()

    first_pass = [classify_lesson(item["claim"], item["source_snippet"]).target.value for item in fixtures]
    second_pass = [classify_lesson(item["claim"], item["source_snippet"]).target.value for item in fixtures]

    assert len(fixtures) == 27
    assert first_pass == [item["expected_target"] for item in fixtures]
    assert second_pass == first_pass
    assert set(first_pass) == {target.value for target in PromotionTarget}


def test_real_session_dogfood_rows_cover_reclassified_targets():
    fixtures = [item for item in load_fixtures() if item["source_session"].startswith("dogfood-")]
    counts = Counter(item["expected_target"] for item in fixtures)

    assert counts == Counter({
        PromotionTarget.REPO_DOCTRINE.value: 3,
        PromotionTarget.SKILL_PATCH.value: 3,
        PromotionTarget.MEMORY.value: 1,
    })


def test_boundary_and_skill_patch_rules_win_before_broad_routing_terms():
    cases = [
        (
            "Interflect proposals must be reviewable before memory, canon, skill, Beads, or routing mutation.",
            "Guardrail: Interflect should propose promotions, not silently rewrite canon or mutate memory/routing.",
            PromotionTarget.REPO_DOCTRINE,
        ),
        (
            "Ockham project doctrine should preserve policy/governance boundaries and avoid becoming a scheduler or monolithic orchestrator.",
            "Ockham was explicitly a policy engine, not an orchestrator; it should not directly dispatch agents.",
            PromotionTarget.REPO_DOCTRINE,
        ),
        (
            "Use the Claude Code plus Oracle prereview procedure before opening or updating upstream PRs.",
            "The user pointed out that a PR was opened/updated before required prereview.",
            PromotionTarget.SKILL_PATCH,
        ),
        (
            "Patch Oracle review skills to avoid bare local-path references; embed prompt contents or use a wrapper that passes files correctly.",
            "Oracle browser mode could not access a local prompt file by path.",
            PromotionTarget.SKILL_PATCH,
        ),
        (
            "General Systems Ventures is the broad umbrella; Sylveste is part of GSV; Interverse is the agent/Claude Code plugin layer.",
            "The user corrected that General Systems Ventures is the broader umbrella.",
            PromotionTarget.MEMORY,
        ),
    ]

    for claim, snippet, expected in cases:
        assert classify_lesson(claim, snippet).target == expected


def test_runtime_only_lessons_include_rejection_reason():
    result = classify_lesson("Port 9119 was listening during the check.", "runtime port snapshot")

    assert result.target == PromotionTarget.RUNTIME_ONLY
    assert "transient" in result.rationale.lower()
    assert result.confidence >= 0.7
