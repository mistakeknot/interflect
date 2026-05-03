from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
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

    def to_json(self) -> dict:
        data = asdict(self)
        data["target"] = self.target.value
        return data

    @classmethod
    def from_json(cls, data: dict) -> "PromotionProposal":
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
        cards.append(
            "\n".join([
                "**Interflect proposal**",
                f"ID: {proposal.idempotency_key}",
                f"Target: {proposal.target.value}",
                f"Status: {proposal.status}",
                f"Confidence: {proposal.confidence:.2f}",
                f"Source: {proposal.source_handle}",
                f"Claim: {proposal.claim}",
                f"Rationale: {proposal.rationale}",
                "No automatic mutation has been applied.",
            ])
        )
    return "\n\n---\n\n".join(cards)
