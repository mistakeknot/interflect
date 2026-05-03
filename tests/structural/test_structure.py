import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_plugin_manifest_declares_interflect_commands_and_metadata():
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())

    assert manifest["name"] == "interflect"
    assert manifest["version"] == "0.1.0"
    assert "retrospective" in manifest["description"].lower()
    assert "./commands/interflect.md" in manifest["commands"]
    assert "./commands/interflect-review.md" in manifest["commands"]
    assert manifest["repository"] == "https://github.com/mistakeknot/interflect"


def test_required_docs_and_command_surfaces_exist():
    for rel in [
        "README.md",
        "AGENTS.md",
        "CLAUDE.md",
        "PHILOSOPHY.md",
        "commands/interflect.md",
        "commands/interflect-review.md",
    ]:
        assert (ROOT / rel).exists(), rel

    command = (ROOT / "commands" / "interflect.md").read_text().lower()
    assert "proposal-only" in command
    assert "no automatic mutation" in command
