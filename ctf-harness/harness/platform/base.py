"""
Abstract platform interface.

A `CTFPlatform` knows how to talk to one specific CTF website: log in, list
challenges, download attached files, and submit flags. The rest of the harness
only ever touches this interface, so supporting a new platform = one new class.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Challenge:
    """One CTF challenge, normalized to a platform-independent shape."""
    id: str
    name: str
    category: str
    description: str
    value: int | None = None
    files: list[str] = field(default_factory=list)   # absolute URLs to attachments
    connection_info: str | None = None               # e.g. "nc host 1337" or a URL
    answer_sha256: str | None = None                 # for platforms that grade by hash
    solved: bool = False

    def short(self) -> str:
        return f"[{self.category}] {self.name} (id={self.id})"


class CTFPlatform(ABC):
    """Interface every platform adapter implements."""

    @abstractmethod
    def login(self) -> None:
        """Authenticate. No-op if the platform is public."""

    @abstractmethod
    def list_challenges(self) -> list[Challenge]:
        """Return all challenges visible to the logged-in user."""

    @abstractmethod
    def download_file(self, url: str, dest_path: str) -> str:
        """Download one attachment to dest_path and return that path."""

    @abstractmethod
    def submit_flag(self, challenge: Challenge, flag: str) -> bool:
        """Submit a candidate flag. Return True iff the platform says it's correct."""


def load_platform(cfg: dict[str, Any], secrets: dict[str, str]) -> CTFPlatform:
    """Instantiate the adapter named in config['platform']['adapter']."""
    name = cfg["platform"]["adapter"]
    if name == "azure_swa":
        from .azure_swa import AzureStaticWebAppPlatform
        return AzureStaticWebAppPlatform(cfg, secrets)
    if name == "mock":
        from .mock import MockPlatform
        return MockPlatform(cfg, secrets)
    raise ValueError(f"Unknown platform adapter: {name!r}")
