"""Discover and track browser-visible CTF challenges without challenge JSON."""
from __future__ import annotations

import csv
import re
import time
from dataclasses import dataclass
from pathlib import Path

from .platform.base import Challenge

_CARD = re.compile(r"(?m)^#(?P<id>\d{3})\s*\n(?P<name>[^\n]+)\s*\n(?P<points>\d+)\s+pts\b")
_CATEGORIES = {"CRYPTOGRAPHY", "WEB EXPLOITATION", "FORENSICS", "REVERSE ENGINEERING", "STEGANOGRAPHY", "OSINT"}


def discover_challenges(text: str, *, include_solved: bool = False) -> list[Challenge]:
    """Parse only rendered card text. Fail closed on incomplete/ambiguous data."""
    result = []
    seen = set()
    for match in _CARD.finditer(text):
        cid = match.group("id")
        name = match.group("name").strip()
        if cid in seen:
            raise ValueError(f"Duplicate challenge ID {cid} in dashboard")
        seen.add(cid)
        # The next card begins at the following card match.
        following = _CARD.search(text, match.end())
        block = text[match.end() : following.start() if following else len(text)]
        if "Solved" in block and "Unsolved" not in block and not include_solved:
            continue
        # Find most recent category header *prior* to the card ID.
        previous = text[:match.start()].splitlines()
        category = next((s.strip().title() for s in reversed(previous) if s.strip() in _CATEGORIES), "Unknown")
        result.append(Challenge(id=cid, name=name, category=category,
                                description="", value=int(match.group("points"))))
    if not result:
        raise ValueError("No CTF challenge cards found on the visible dashboard")
    return result


DETAIL_FIELDS = ["run_id", "challenge_id", "challenge_name", "category", "points", "solved",
                 "attempts", "agent_steps", "agent_wall_seconds", "challenge_seconds",
                 "input_tokens", "output_tokens", "failure_reason", "timing_note"]


class ChallengeMetrics:
    """Capture browser open and submission times, keeping log times distinct."""
    def __init__(self, challenge: Challenge, sink):
        self.challenge = challenge
        self.sink = sink
        self.started_at = None
        self.last_submission_at = None
        self.attempts = 0

    def event(self, kind: str, data: dict) -> None:
        # Agent's browser_click event is emitted after the click operation.
        if kind == "observation" and str(data.get("text", "")).startswith(f"Clicked: {self.challenge.name}\n"):
            self.started_at = self.started_at or time.monotonic()
        if kind == "action" and data.get("tool") == "submit_flag":
            self.attempts += 1
            self.last_submission_at = time.monotonic()
        self.sink(kind, data)

    def seconds(self) -> float | None:
        if self.started_at is None:
            return None
        return round((self.last_submission_at or time.monotonic()) - self.started_at, 2)


def write_challenge_metrics(csv_path: str | Path, run_id: str, ch: Challenge, result,
                            metrics: ChallengeMetrics) -> None:
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=DETAIL_FIELDS)
        if new:
            writer.writeheader()
        writer.writerow({
            "run_id": run_id, "challenge_id": ch.id, "challenge_name": ch.name,
            "category": ch.category, "points": ch.value, "solved": result.solved,
            "attempts": metrics.attempts, "agent_steps": result.steps,
            "agent_wall_seconds": result.wall_seconds, "challenge_seconds": metrics.seconds(),
            "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
            "failure_reason": result.failure_reason or "",
            "timing_note": "Approx. time from browser click to last submission (or agent stop); not the platform's timer",
        })
