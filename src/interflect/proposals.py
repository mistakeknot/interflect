from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Iterable

from .taxonomy import Classification, PromotionTarget, classify_lesson


@dataclass(frozen=True)
class LessonCandidate:
    source_session: str
    source_handle: str
    source_snippet: str
    claim: str


@dataclass(frozen=True)
class PromotionProposal:
    idempotency_key: str
    source_session: str
    source_handle: str
    source_snippet: str
    claim: str
    target: PromotionTarget
    confidence: float
    rationale: str
    status: str = "proposed"
    review_decision: str | None = None
    final_target: PromotionTarget | None = None
    review_rationale: str | None = None
    reviewed_at: str | None = None

    def to_json(self) -> dict:
        data = asdict(self)
        data["target"] = self.target.value
        if self.final_target is not None:
            data["final_target"] = self.final_target.value
        return {key: value for key, value in data.items() if value is not None}

    @classmethod
    def from_json(cls, data: dict) -> "PromotionProposal":
        final_target = data.get("final_target")
        return cls(
            idempotency_key=data["idempotency_key"],
            source_session=data["source_session"],
            source_handle=data["source_handle"],
            source_snippet=data.get("source_snippet", ""),
            claim=data["claim"],
            target=PromotionTarget(data["target"]),
            confidence=float(data["confidence"]),
            rationale=data["rationale"],
            status=data.get("status", "proposed"),
            review_decision=data.get("review_decision"),
            final_target=PromotionTarget(final_target) if final_target else None,
            review_rationale=data.get("review_rationale"),
            reviewed_at=data.get("reviewed_at"),
        )


def normalize_claim(claim: str) -> str:
    return " ".join(claim.strip().lower().split())


def idempotency_key(candidate: LessonCandidate, classification: Classification) -> str:
    raw = "\x1f".join([
        candidate.source_session.strip(),
        normalize_claim(candidate.claim),
        classification.target.value,
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


class ProposalQueue:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def load(self) -> list[PromotionProposal]:
        if not self.path.exists():
            return []
        proposals: list[PromotionProposal] = []
        for line in self.path.read_text().splitlines():
            if line.strip():
                proposals.append(PromotionProposal.from_json(json.loads(line)))
        return proposals

    def _write_all(self, proposals: Iterable[PromotionProposal]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            for proposal in proposals:
                fh.write(json.dumps(proposal.to_json(), ensure_ascii=False, separators=(",", ":")) + "\n")

    def add(self, candidate: LessonCandidate) -> PromotionProposal:
        classification = classify_lesson(candidate.claim, candidate.source_snippet)
        key = idempotency_key(candidate, classification)
        existing = {proposal.idempotency_key: proposal for proposal in self.load()}
        if key in existing:
            return existing[key]

        proposal = PromotionProposal(
            idempotency_key=key,
            source_session=candidate.source_session,
            source_handle=candidate.source_handle,
            source_snippet=candidate.source_snippet,
            claim=candidate.claim,
            target=classification.target,
            confidence=classification.confidence,
            rationale=classification.rationale,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(proposal.to_json(), ensure_ascii=False, separators=(",", ":")) + "\n")
        return proposal

    def record_review(
        self,
        proposal_id: str,
        *,
        decision: str,
        final_target: PromotionTarget | str | None = None,
        rationale: str = "",
        reviewed_at: str | None = None,
    ) -> PromotionProposal:
        if decision not in {"accepted", "reclassified", "rejected"}:
            raise ValueError("decision must be accepted, reclassified, or rejected")

        final_target_enum = None
        if final_target is not None:
            final_target_enum = final_target if isinstance(final_target, PromotionTarget) else PromotionTarget(final_target)

        proposals = self.load()
        updated: list[PromotionProposal] = []
        reviewed: PromotionProposal | None = None
        for proposal in proposals:
            if proposal.idempotency_key == proposal_id:
                reviewed = replace(
                    proposal,
                    status="reviewed",
                    review_decision=decision,
                    final_target=final_target_enum or proposal.target,
                    review_rationale=rationale,
                    reviewed_at=reviewed_at,
                )
                updated.append(reviewed)
            else:
                updated.append(proposal)

        if reviewed is None:
            raise KeyError(f"proposal not found: {proposal_id}")

        self._write_all(updated)
        return reviewed


def candidates_from_jsonl(path: Path | str) -> Iterable[LessonCandidate]:
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        yield LessonCandidate(
            source_session=obj["source_session"],
            source_handle=obj.get("source_handle", obj["source_session"]),
            source_snippet=obj.get("source_snippet", ""),
            claim=obj["claim"],
        )


def render_review_cards(proposals: Iterable[PromotionProposal]) -> str:
    cards: list[str] = []
    for proposal in proposals:
        lines = [
            "**Interflect proposal**",
            f"ID: {proposal.idempotency_key}",
            f"Target: {proposal.target.value}",
            f"Status: {proposal.status}",
            f"Confidence: {proposal.confidence:.2f}",
            f"Source: {proposal.source_handle}",
            f"Claim: {proposal.claim}",
            f"Rationale: {proposal.rationale}",
        ]
        if proposal.review_decision:
            lines.extend([
                f"Review decision: {proposal.review_decision}",
                f"Final target: {proposal.final_target.value if proposal.final_target else proposal.target.value}",
                f"Review rationale: {proposal.review_rationale or ''}",
            ])
        lines.append("No automatic mutation has been applied.")
        cards.append("\n".join(lines))
    return "\n\n---\n\n".join(cards)
