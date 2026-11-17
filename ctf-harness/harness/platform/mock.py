"""
A fake in-memory platform for testing the harness plumbing without a live site.
Enable it by setting platform.adapter: "mock" in config.yaml.

The one challenge's flag is literally sitting in the description, so even a weak
model (or the offline self-check) can "solve" it — useful to prove the end-to-end
loop works before you point it at the real platform.
"""
from __future__ import annotations

from typing import Any

from .base import Challenge, CTFPlatform

_FLAG = "FGCU{mock_pipeline_works}"


class MockPlatform(CTFPlatform):
    def __init__(self, cfg: dict[str, Any], secrets: dict[str, str]):
        self.cfg = cfg
        self._submitted: list[tuple[str, str]] = []

    def login(self) -> None:
        return

    def list_challenges(self) -> list[Challenge]:
        return [
            Challenge(
                id="1",
                name="sanity-check",
                category="misc",
                description=(
                    "Warm-up. Run `echo` to print this exact flag, then submit it: "
                    + _FLAG
                ),
                value=10,
            )
        ]

    def download_file(self, url: str, dest_path: str) -> str:
        return dest_path

    def submit_flag(self, challenge: Challenge, flag: str) -> bool:
        self._submitted.append((challenge.id, flag))
        return flag.strip() == _FLAG
