from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .proposals import LessonCandidate, normalize_claim


@dataclass(frozen=True)
class SessionRecord:
    source_session: str
    source_handle: str
    content: str


def _stringify_messages(messages: object) -> str:
    if not isinstance(messages, list):
        return ""
    parts: list[str] = []
    for message in messages:
        if isinstance(message, str):
            parts.append(message)
        elif isinstance(message, dict):
            author = message.get("author") or message.get("role") or message.get("sender") or ""
            body = message.get("content") or message.get("text") or message.get("message") or ""
            if body:
                parts.append(f"{author}: {body}" if author else str(body))
    return "\n".join(parts)


def _record_from_json(obj: dict) -> SessionRecord:
    source_session = str(
        obj.get("source_session")
        or obj.get("session_id")
        or obj.get("session")
        or obj.get("id")
        or obj.get("handle")
        or "unknown-session"
    )
    title = str(obj.get("title") or obj.get("name") or "").strip()
    source_handle = str(obj.get("source_handle") or obj.get("handle") or f"session_search:{source_session} {title}".strip())
    raw_locator = obj.get("permalink") or obj.get("url") or obj.get("source_url")
    if raw_locator and str(raw_locator) not in source_handle:
        source_handle = f"{source_handle} <{raw_locator}>"
    content_parts = [
        obj.get("summary"),
        obj.get("description"),
        obj.get("content"),
        obj.get("text"),
        _stringify_messages(obj.get("messages")),
    ]
    content = "\n".join(str(part) for part in content_parts if part)
    return SessionRecord(source_session=source_session, source_handle=source_handle, content=content)


def session_records_from_jsonl(path: Path | str) -> Iterable[SessionRecord]:
    """Read session_search/CASS-style summary records from JSONL.

    Supported record shapes are intentionally loose: `session_id`,
    `source_session`, `id`, or `handle` identify the session; summary text can
    live in `summary`, `description`, `content`, `text`, or a `messages` list.
    """
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        yield _record_from_json(json.loads(line))


def _sentences(text: str) -> Iterable[str]:
    cleaned = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
    if not cleaned:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]


def _looks_like_lesson(sentence: str) -> bool:
    text = sentence.lower()
    if text.startswith(("the assistant opened", "ordinary task")) or "should not become a lesson" in text:
        return False
    signal_terms = (
        " corrected ",
        "guardrail",
        "prefers",
        "preference",
        "project doctrine",
        "boundary",
        "boundaries",
        " should ",
        " must ",
        "avoid ",
        "use the ",
        "use ",
        "patch ",
        "prereview",
        "wrapper",
        "pitfall",
        "follow-up",
        "beads follow-up",
        "routing should",
        "route ",
        "codex",
        "claude code",
        "port ",
        "runtime check",
    )
    return any(term in f" {text} " for term in signal_terms)


def _claim_from_sentence(sentence: str) -> str:
    claim = sentence.strip().lstrip("-*• ").strip()
    prefix, sep, rest = claim.partition(":")
    if sep and any(term in prefix.lower() for term in ("corrected", "guardrail", "lesson", "finding", "note")):
        claim = rest.strip()
    claim = re.sub(r"^mk:\s*", "", claim, flags=re.IGNORECASE).strip()
    if claim and claim[-1] not in ".!?":
        claim += "."
    return claim


def candidates_from_session_records(records: Iterable[SessionRecord]) -> Iterable[LessonCandidate]:
    seen: set[tuple[str, str]] = set()
    for record in records:
        for sentence in _sentences(record.content):
            if not _looks_like_lesson(sentence):
                continue
            claim = _claim_from_sentence(sentence)
            if not claim:
                continue
            key = (record.source_session, normalize_claim(claim))
            if key in seen:
                continue
            seen.add(key)
            yield LessonCandidate(
                source_session=record.source_session,
                source_handle=record.source_handle,
                source_snippet=sentence,
                claim=claim,
            )


def candidates_from_session_summaries(path: Path | str) -> Iterable[LessonCandidate]:
    return candidates_from_session_records(session_records_from_jsonl(path))
