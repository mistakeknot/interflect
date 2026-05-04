import json
from pathlib import Path

from interflect.sources import candidates_from_session_summaries, session_records_from_jsonl
from interflect.taxonomy import classify_lesson


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "session_summaries.jsonl"


def test_session_records_from_jsonl_accept_session_search_shape():
    records = list(session_records_from_jsonl(FIXTURE_PATH))

    assert records[0].source_session == "20260503_070215_236908cc"
    assert records[0].source_handle == "session_search:20260503_070215_236908cc Interflect sprint clarification"
    assert "Interflect is the active project identity" in records[0].content


def test_session_summary_adapter_extracts_candidate_lessons_with_source_fields():
    candidates = list(candidates_from_session_summaries(FIXTURE_PATH))

    assert len(candidates) == 9
    assert {candidate.source_session for candidate in candidates} == {
        "20260503_070215_236908cc",
        "20260418_111909_5169e51b",
        "20260408_073431_99def2b6",
        "20260423_051132_f7316241",
        "20260503_followup",
        "20260424_runtime",
    }
    assert all(candidate.source_handle.startswith("session_search:") for candidate in candidates)
    assert all(candidate.source_snippet for candidate in candidates)
    assert all(candidate.claim.endswith(".") for candidate in candidates)
    assert "ordinary task" not in " ".join(candidate.claim for candidate in candidates)


def test_extracted_candidates_cover_taxonomy_targets_deterministically():
    candidates = list(candidates_from_session_summaries(FIXTURE_PATH))
    targets = [classify_lesson(candidate.claim, candidate.source_snippet).target.value for candidate in candidates]

    assert targets == [
        "repo_doctrine",
        "repo_doctrine",
        "memory",
        "repo_doctrine",
        "routing_signal",
        "skill_patch",
        "skill_patch",
        "beads_followup",
    ] + ["runtime_only"]
