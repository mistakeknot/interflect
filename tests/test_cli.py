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
    assert stored[0]["target"] == "memory"
    assert stored[0]["status"] == "proposed"
    assert stored[0]["source_session"] == "sess-001"
    assert "Interflect proposal" in result.stdout
    assert "No automatic mutation has been applied" in result.stdout
