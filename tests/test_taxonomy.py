import json
from pathlib import Path

from interflect.taxonomy import PromotionTarget, classify_lesson


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "lessons.jsonl"


def load_fixtures():
    return [json.loads(line) for line in FIXTURE_PATH.read_text().splitlines() if line.strip()]


def test_twenty_fixture_lessons_classify_deterministically_across_all_targets():
    fixtures = load_fixtures()

    first_pass = [classify_lesson(item["claim"], item["source_snippet"]).target.value for item in fixtures]
    second_pass = [classify_lesson(item["claim"], item["source_snippet"]).target.value for item in fixtures]

    assert len(fixtures) == 20
    assert first_pass == [item["expected_target"] for item in fixtures]
    assert second_pass == first_pass
    assert set(first_pass) == {target.value for target in PromotionTarget}


def test_runtime_only_lessons_include_rejection_reason():
    result = classify_lesson("Port 9119 was listening during the check.", "runtime port snapshot")

    assert result.target == PromotionTarget.RUNTIME_ONLY
    assert "transient" in result.rationale.lower()
    assert result.confidence >= 0.7
