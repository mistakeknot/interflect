from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from pathlib import Path
from typing import Iterable

from .proposals import PromotionProposal
from .taxonomy import PromotionTarget


class ApplyRefusal(ValueError):
    """Raised when a proposal is not eligible for even a safe draft apply path."""


@dataclass(frozen=True)
class ApplyDraft:
    proposal_id: str
    target: PromotionTarget
    artifact_path: Path
    mutation_applied: bool
    duplicate_matches: list[dict]
    message: str

    def to_json(self) -> dict:
        data = asdict(self)
        data["target"] = self.target.value
        data["artifact_path"] = str(self.artifact_path)
        return data


def effective_target(proposal: PromotionProposal) -> PromotionTarget:
    return proposal.final_target or proposal.target


def require_applyable_review(proposal: PromotionProposal) -> PromotionTarget:
    """Validate the review gate for safe draft appliers.

    Interflect appliers never run from raw classifier output. A proposal must
    have explicit human review state, and the human decision must be accepted or
    reclassified. Even then, runtime-only remains non-applyable.
    """
    if proposal.status != "reviewed":
        raise ApplyRefusal("proposal must be reviewed before any apply path can run")
    if proposal.review_decision not in {"accepted", "reclassified"}:
        raise ApplyRefusal("proposal review_decision must be accepted or reclassified before apply")
    target = effective_target(proposal)
    if target == PromotionTarget.RUNTIME_ONLY:
        raise ApplyRefusal("runtime_only proposals are not applyable")
    return target


def _slug(text: str, limit: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:limit].strip("-") or "proposal")


def _tokenize(text: str) -> set[str]:
    stop = {
        "the", "and", "for", "with", "that", "this", "from", "into", "should", "create", "proposal", "proposals",
    }
    return {token for token in re.findall(r"[a-z0-9]{2,}", text.lower()) if token not in stop}


def load_jsonl_records(path: Path | str) -> list[dict]:
    records: list[dict] = []
    jsonl = Path(path)
    if not jsonl.exists():
        return records
    for line in jsonl.read_text().splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def find_beads_duplicates(proposal: PromotionProposal, existing_beads: Iterable[dict], *, limit: int = 5) -> list[dict]:
    """Return likely duplicate Beads based on transparent lexical overlap.

    This is a conservative draft-time search helper, not authority. The CLI
    surfaces candidates so the operator can choose whether to create a new bead.
    """
    claim_norm = " ".join(proposal.claim.lower().split())
    claim_tokens = _tokenize(proposal.claim)
    matches: list[tuple[int, dict]] = []
    for bead in existing_beads:
        haystack = " ".join(str(bead.get(key, "")) for key in ("id", "title", "description", "notes", "status"))
        haystack_norm = " ".join(haystack.lower().split())
        haystack_tokens = _tokenize(haystack)
        overlap = claim_tokens & haystack_tokens
        score = len(overlap)
        if claim_norm and (claim_norm in haystack_norm or haystack_norm in claim_norm):
            score += 8
        if score >= 2:
            matches.append((score, {
                "id": str(bead.get("id", "")),
                "title": str(bead.get("title", "")),
                "status": str(bead.get("status", "")),
                "overlap_terms": sorted(overlap),
                "score": score,
            }))
    matches.sort(key=lambda item: (-item[0], item[1].get("id", "")))
    return [match for _, match in matches[:limit]]


def _artifact_base(proposal: PromotionProposal, target: PromotionTarget) -> str:
    return f"{proposal.idempotency_key}-{target.value}-{_slug(proposal.claim)}.md"


def _write_artifact(artifact_dir: Path | str, filename: str, content: str) -> Path:
    directory = Path(artifact_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_text(content, encoding="utf-8")
    return path


def _render_header(proposal: PromotionProposal, target: PromotionTarget) -> str:
    return "\n".join([
        f"# Interflect apply draft: `{proposal.idempotency_key}`",
        "",
        f"- Target: `{target.value}`",
        f"- Review decision: `{proposal.review_decision}`",
        f"- Review rationale: {proposal.review_rationale or ''}",
        f"- Source: {proposal.source_handle}",
        f"- Claim: {proposal.claim}",
        "",
    ])


def _render_beads_draft(proposal: PromotionProposal, target: PromotionTarget, duplicates: list[dict]) -> str:
    title = proposal.claim.rstrip(".")
    body = proposal.source_snippet or proposal.claim
    duplicate_lines = ["No likely duplicate Beads were found in the provided search corpus."]
    if duplicates:
        duplicate_lines = [
            f"- `{item['id']}` — {item['title']} ({item['status']}; overlap: {', '.join(item['overlap_terms']) or 'n/a'})"
            for item in duplicates
        ]
    command = (
        "bd create --type task --priority 2 "
        f"--title {json.dumps(title)} "
        f"--body {json.dumps(body + '\\n\\nSource: ' + proposal.source_handle)}"
    )
    return _render_header(proposal, target) + "\n".join([
        "## DRY RUN Beads follow-up draft",
        "",
        "No Beads mutation has been applied. Review duplicate candidates before running any command.",
        "",
        "### Likely duplicate candidates",
        *duplicate_lines,
        "",
        "### Draft command",
        "",
        "```bash",
        command,
        "```",
        "",
    ])


def _render_patch_artifact(proposal: PromotionProposal, target: PromotionTarget, patch_target: Path | str | None) -> str:
    target_path = Path(patch_target) if patch_target else Path("<choose-target-file>")
    basename = target_path.name if str(target_path) != "<choose-target-file>" else "TARGET.md"
    return _render_header(proposal, target) + "\n".join([
        "## DRY RUN patch artifact",
        "",
        "No target file has been modified. Copy, edit, and apply this patch only after explicit operator approval.",
        "",
        "```diff",
        f"diff --git a/{target_path} b/{target_path}",
        f"--- a/{target_path}",
        f"+++ b/{target_path}",
        f"@@ {basename} @@",
        f"+<!-- Interflect reviewed proposal {proposal.idempotency_key} -->",
        f"+- {proposal.claim}",
        f"+  - Source: {proposal.source_handle}",
        f"+  - Review: {proposal.review_rationale or proposal.rationale}",
        "```",
        "",
    ])


def _render_explicit_approval_stub(proposal: PromotionProposal, target: PromotionTarget) -> str:
    substrate = "memory" if target == PromotionTarget.MEMORY else "routing overlay"
    return _render_header(proposal, target) + "\n".join([
        "## EXPLICIT APPROVAL REQUIRED",
        "",
        f"Interflect does not mutate {substrate} from v0 apply drafts.",
        "No mutation has been applied.",
        "",
        "### Proposed text",
        "",
        f"> {proposal.claim}",
        "",
        "### Rollback",
        "",
        f"If a future approved operator applies this to {substrate}, rollback must remove the exact added entry and record the proposal ID:",
        f"`{proposal.idempotency_key}`.",
        "",
    ])


def apply_reviewed_proposal(
    proposal: PromotionProposal,
    *,
    artifact_dir: Path | str,
    existing_beads: Iterable[dict] = (),
    patch_target: Path | str | None = None,
) -> ApplyDraft:
    target = require_applyable_review(proposal)
    duplicates: list[dict] = []
    filename = _artifact_base(proposal, target)

    if target == PromotionTarget.BEADS_FOLLOWUP:
        duplicates = find_beads_duplicates(proposal, existing_beads)
        content = _render_beads_draft(proposal, target, duplicates)
        message = "dry-run Beads follow-up draft emitted"
    elif target in {PromotionTarget.SKILL_PATCH, PromotionTarget.REPO_DOCTRINE}:
        content = _render_patch_artifact(proposal, target, patch_target)
        message = "dry-run patch artifact emitted"
    elif target in {PromotionTarget.MEMORY, PromotionTarget.ROUTING_SIGNAL}:
        content = _render_explicit_approval_stub(proposal, target)
        message = "explicit-approval stub emitted"
    else:
        raise ApplyRefusal(f"target is not applyable: {target.value}")

    path = _write_artifact(artifact_dir, filename, content)
    return ApplyDraft(
        proposal_id=proposal.idempotency_key,
        target=target,
        artifact_path=path,
        mutation_applied=False,
        duplicate_matches=duplicates,
        message=message,
    )
