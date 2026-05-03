from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class PromotionTarget(str, Enum):
    MEMORY = "memory"
    SKILL_PATCH = "skill_patch"
    REPO_DOCTRINE = "repo_doctrine"
    BEADS_FOLLOWUP = "beads_followup"
    ROUTING_SIGNAL = "routing_signal"
    RUNTIME_ONLY = "runtime_only"


@dataclass(frozen=True)
class Classification:
    target: PromotionTarget
    confidence: float
    rationale: str


def _text(*parts: str) -> str:
    return " ".join(p or "" for p in parts).lower()


def classify_lesson(claim: str, source_snippet: str = "") -> Classification:
    """Classify a lesson into Interflect's v0 promotion taxonomy.

    The v0 classifier is intentionally deterministic and conservative. It uses
    transparent lexical rules so proposal output is reviewable and predictable;
    later model-assisted extraction can feed this classifier rather than replace
    the review boundary.
    """
    text = _text(claim, source_snippet)

    runtime_phrases = ("current", "during this session", "right now", "one-time", "pycache", "runtime date", "listening")
    if any(term in text for term in runtime_phrases) or re.search(r"\bport\s+\d+\b", text):
        return Classification(
            PromotionTarget.RUNTIME_ONLY,
            0.78,
            "Transient runtime/session state; keep in handoff only if still relevant.",
        )

    followup_terms = ("create follow-up", "follow-up bead", "file follow-up", "implementation bead", "create a beads follow-up")
    if any(term in text for term in followup_terms):
        return Classification(
            PromotionTarget.BEADS_FOLLOWUP,
            0.86,
            "Actionable future work belongs in Beads before any durable canon change.",
        )

    memory_terms = ("mk", "prefers", "likes", "refers to", "not gsv", "preference", "identity")
    if any(term in text for term in memory_terms):
        return Classification(
            PromotionTarget.MEMORY,
            0.83,
            "Stable user/project identity fact is a candidate for compact memory.",
        )

    if "interflect" in text and "interspect" in text:
        return Classification(
            PromotionTarget.REPO_DOCTRINE,
            0.88,
            "Interflect/Interspect boundary belongs in repo doctrine/specs.",
        )

    routing_terms = ("route", "routing", "agent", "review agent", "codex", "claude code", "browser qa", "underperformed")
    if any(term in text for term in routing_terms):
        return Classification(
            PromotionTarget.ROUTING_SIGNAL,
            0.82,
            "Lesson affects future body/model/tool routing rather than prose canon directly.",
        )

    skill_terms = ("use argv", "shell", "beads mutation", "auto-export", "blocked bundle", "split verification", "procedure", "pitfall")
    if any(term in text for term in skill_terms):
        return Classification(
            PromotionTarget.SKILL_PATCH,
            0.84,
            "Reusable operational procedure or pitfall should become a skill patch.",
        )

    doctrine_terms = ("interflect", "interspect", "canon", "doctrine", "project work", "hermes integration", "sylveste", "proposal", "promotion", "reviewable")
    if any(term in text for term in doctrine_terms):
        return Classification(
            PromotionTarget.REPO_DOCTRINE,
            0.8,
            "Project-local boundary or operating rule belongs in repo doctrine/specs.",
        )

    return Classification(
        PromotionTarget.RUNTIME_ONLY,
        0.51,
        "No durable promotion target is clear; hold as runtime-only unless reviewed.",
    )
