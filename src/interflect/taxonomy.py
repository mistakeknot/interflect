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


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def classify_lesson(claim: str, source_snippet: str = "") -> Classification:
    """Classify a lesson into Interflect's v0 promotion taxonomy.

    The v0 classifier is intentionally deterministic and conservative. It uses
    transparent lexical rules so proposal output is reviewable and predictable;
    later model-assisted extraction can feed this classifier rather than replace
    the review boundary.
    """
    text = _text(claim, source_snippet)

    runtime_phrases = ("current", "during this session", "right now", "one-time", "pycache", "runtime date", "listening")
    if _has_any(text, runtime_phrases) or re.search(r"\bport\s+\d+\b", text):
        return Classification(
            PromotionTarget.RUNTIME_ONLY,
            0.78,
            "Transient runtime/session state; keep in handoff only if still relevant.",
        )

    followup_terms = ("create follow-up", "follow-up bead", "file follow-up", "implementation bead", "create a beads follow-up")
    if _has_any(text, followup_terms):
        return Classification(
            PromotionTarget.BEADS_FOLLOWUP,
            0.86,
            "Actionable future work belongs in Beads before any durable canon change.",
        )

    # Project-boundary and proposal-safety rules must win before broad memory or
    # routing terms. Real-session dogfood showed that words like "identity",
    # "routing", and "agent" can appear inside doctrine claims without making
    # the lesson a memory entry or routing signal.
    if "interflect" in text and "interspect" in text:
        return Classification(
            PromotionTarget.REPO_DOCTRINE,
            0.9,
            "Interflect/Interspect boundary belongs in repo doctrine/specs.",
        )

    doctrine_boundary_terms = (
        "project doctrine",
        "repo doctrine",
        "boundary",
        "boundaries",
        "positioning boundary",
        "canonical home",
        "proposal-first",
        "review-before-mutation",
    )
    if _has_any(text, doctrine_boundary_terms):
        return Classification(
            PromotionTarget.REPO_DOCTRINE,
            0.86,
            "Project-local boundary or operating rule belongs in repo doctrine/specs.",
        )

    if "interflect" in text and _has_any(text, ("reviewable", "proposal", "proposals", "mutation", "mutate", "silently rewrite")):
        return Classification(
            PromotionTarget.REPO_DOCTRINE,
            0.87,
            "Interflect review-before-mutation guardrail belongs in repo doctrine/specs.",
        )

    if "ockham" in text and _has_any(text, ("policy", "governance", "orchestrator", "scheduler", "dispatch agents")):
        return Classification(
            PromotionTarget.REPO_DOCTRINE,
            0.87,
            "Ockham policy/governance boundary belongs in repo doctrine/specs.",
        )

    skill_terms = (
        "use argv",
        "shell",
        "beads mutation",
        "auto-export",
        "blocked bundle",
        "split verification",
        "procedure",
        "pitfall",
        "prereview",
        "pre-review",
        "oracle review",
        "review skill",
        "review skills",
        "workflow procedure",
        "wrapper",
        "review-planning",
        "verdict taxonomy",
    )
    patch_skill_pattern = re.search(r"\bpatch\b.*\bskills?\b", text) or re.search(r"\bskills?\b.*\bpatch\b", text)
    if _has_any(text, skill_terms) or patch_skill_pattern:
        return Classification(
            PromotionTarget.SKILL_PATCH,
            0.86,
            "Reusable operational procedure or pitfall should become a skill patch.",
        )

    memory_terms = (
        "mk",
        "prefers",
        "likes",
        "refers to",
        "not gsv",
        "preference",
        "general systems ventures is the broad umbrella",
        "broader umbrella",
    )
    if _has_any(text, memory_terms):
        return Classification(
            PromotionTarget.MEMORY,
            0.83,
            "Stable user/project identity fact is a candidate for compact memory.",
        )

    routing_patterns = (
        re.search(r"\b(should\s+)?route\b", text),
        re.search(r"\brouting\s+should\b", text),
        "browser qa" in text,
        "underperformed" in text and _has_any(text, ("agent", "model", "review")),
        "should be considered" in text and _has_any(text, ("codex", "claude code", "model")),
        _has_any(text, ("model/tool routing", "body/model/tool", "dispatch/routing")),
    )
    if any(routing_patterns):
        return Classification(
            PromotionTarget.ROUTING_SIGNAL,
            0.82,
            "Lesson affects future body/model/tool routing rather than prose canon directly.",
        )

    doctrine_terms = ("interflect", "interspect", "canon", "doctrine", "project work", "hermes integration", "sylveste", "proposal", "promotion", "reviewable")
    if _has_any(text, doctrine_terms):
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
