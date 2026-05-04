import json
import os
import subprocess
import sys
from pathlib import Path


def test_cli_analyze_ingests_jsonl_writes_deduped_proposals_and_cards(tmp_path):
    source = tmp_path / "lessons.jsonl"
    store = tmp_path / "proposals.jsonl"
    source.write_text("\n".join([
        json.dumps({
            "source_session": "sess-001",
            "source_handle": "discord:test",
            "source_snippet": "mk: wait i thought we're doing interflect",
            "claim": "Interflect is the active project identity, not Interspect.",
        }),
        json.dumps({
            "source_session": "sess-001",
            "source_handle": "discord:test",
            "source_snippet": "mk: wait i thought we're doing interflect",
            "claim": "Interflect is the active project identity, not Interspect.",
        }),
    ]) + "\n")

    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "interflect.cli",
            "analyze",
            "--input-jsonl",
            str(source),
            "--store",
            str(store),
            "--cards",
            "--session",
            "sess-001",
            "--recent",
            "7d",
        ],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )

    stored = [json.loads(line) for line in store.read_text().splitlines() if line.strip()]
    assert len(stored) == 1
    assert stored[0]["target"] == "repo_doctrine"
    assert stored[0]["status"] == "proposed"
    assert stored[0]["source_session"] == "sess-001"
    assert "Interflect proposal" in result.stdout
    assert "No automatic mutation has been applied" in result.stdout


def test_cli_review_updates_existing_proposal_state(tmp_path):
    source = tmp_path / "lessons.jsonl"
    store = tmp_path / "proposals.jsonl"
    source.write_text(json.dumps({
        "source_session": "sess-002",
        "source_handle": "discord:oracle",
        "source_snippet": "Oracle browser mode could not access a local prompt file by path.",
        "claim": "Patch Oracle review skills to avoid bare local-path references; embed prompt contents or use a wrapper that passes files correctly.",
    }) + "\n")

    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    subprocess.run(
        [sys.executable, "-m", "interflect.cli", "analyze", "--input-jsonl", str(source), "--store", str(store)],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    proposal_id = json.loads(store.read_text().strip())["idempotency_key"]

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "interflect.cli",
            "review",
            "--store",
            str(store),
            "--proposal-id",
            proposal_id,
            "--decision",
            "reclassified",
            "--final-target",
            "skill_patch",
            "--rationale",
            "Reusable Oracle review procedure pitfall.",
            "--reviewed-at",
            "2026-05-04T08:40:00Z",
        ],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )

    stored = json.loads(store.read_text().strip())
    assert stored["status"] == "reviewed"
    assert stored["review_decision"] == "reclassified"
    assert stored["final_target"] == "skill_patch"
    assert stored["review_rationale"] == "Reusable Oracle review procedure pitfall."
    assert json.loads(result.stdout)["review_decision"] == "reclassified"


def test_cli_extract_emits_candidates_from_session_summaries(tmp_path):
    source = Path(__file__).parent / "fixtures" / "session_summaries.jsonl"
    output = tmp_path / "candidates.jsonl"

    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "interflect.cli",
            "extract",
            "--session-jsonl",
            str(source),
            "--output-jsonl",
            str(output),
        ],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )

    rows = [json.loads(line) for line in output.read_text().splitlines() if line.strip()]
    assert len(rows) == 9
    assert rows[0]["source_handle"].startswith("session_search:20260503_070215_236908cc")
    assert rows[0]["claim"] == "Interflect is the active project identity, not Interspect."


def test_cli_extract_can_feed_proposals_and_cards(tmp_path):
    source = Path(__file__).parent / "fixtures" / "session_summaries.jsonl"
    store = tmp_path / "proposals.jsonl"

    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "interflect.cli",
            "extract",
            "--session-jsonl",
            str(source),
            "--store",
            str(store),
            "--cards",
            "--session",
            "20260503_followup",
        ],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )

    stored = [json.loads(line) for line in store.read_text().splitlines() if line.strip()]
    assert len(stored) == 1
    assert stored[0]["target"] == "beads_followup"
    assert "Interflect proposal" in result.stdout
    assert "Target: beads_followup" in result.stdout


def test_cli_apply_refuses_unreviewed_proposals(tmp_path):
    source = tmp_path / "lessons.jsonl"
    store = tmp_path / "proposals.jsonl"
    source.write_text(json.dumps({
        "source_session": "sess-followup",
        "source_handle": "session:todo",
        "source_snippet": "create a follow-up bead",
        "claim": "Create a Beads follow-up for Interflect safe applier UX.",
    }) + "\n")

    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    subprocess.run(
        [sys.executable, "-m", "interflect.cli", "analyze", "--input-jsonl", str(source), "--store", str(store)],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    proposal_id = json.loads(store.read_text().strip())["idempotency_key"]

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "interflect.cli",
            "apply",
            "--store",
            str(store),
            "--proposal-id",
            proposal_id,
            "--artifact-dir",
            str(tmp_path / "artifacts"),
        ],
        text=True,
        capture_output=True,
        env=env,
    )

    assert result.returncode == 1
    assert "reviewed" in result.stderr
    assert not (tmp_path / "artifacts").exists()


def test_cli_apply_writes_dry_run_beads_draft_for_reviewed_proposal(tmp_path):
    source = tmp_path / "lessons.jsonl"
    store = tmp_path / "proposals.jsonl"
    existing = tmp_path / "existing-beads.jsonl"
    source.write_text(json.dumps({
        "source_session": "sess-followup",
        "source_handle": "session:todo",
        "source_snippet": "create a follow-up bead",
        "claim": "Create a Beads follow-up for Interflect safe applier UX.",
    }) + "\n")
    existing.write_text(json.dumps({
        "id": "sylveste-dupe",
        "title": "Interflect safe applier UX follow-up",
        "description": "Draft Beads creation should search duplicates first.",
        "status": "open",
    }) + "\n")

    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    subprocess.run(
        [sys.executable, "-m", "interflect.cli", "analyze", "--input-jsonl", str(source), "--store", str(store)],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    proposal_id = json.loads(store.read_text().strip())["idempotency_key"]
    subprocess.run(
        [
            sys.executable,
            "-m",
            "interflect.cli",
            "review",
            "--store",
            str(store),
            "--proposal-id",
            proposal_id,
            "--decision",
            "accepted",
            "--final-target",
            "beads_followup",
            "--rationale",
            "track implementation follow-up",
            "--reviewed-at",
            "2026-05-04T15:10:00Z",
        ],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "interflect.cli",
            "apply",
            "--store",
            str(store),
            "--proposal-id",
            proposal_id,
            "--artifact-dir",
            str(tmp_path / "artifacts"),
            "--existing-beads-jsonl",
            str(existing),
        ],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )

    summary = json.loads(result.stdout)
    artifact = Path(summary["artifact_path"])
    assert summary["mutation_applied"] is False
    assert summary["target"] == "beads_followup"
    assert artifact.exists()
    assert "sylveste-dupe" in artifact.read_text()
    assert "No Beads mutation has been applied" in artifact.read_text()
