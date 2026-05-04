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
