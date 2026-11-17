"""Platform adapters: the bridge between a live CTF site and the harness."""
from .base import Challenge, CTFPlatform, load_platform

__all__ = ["Challenge", "CTFPlatform", "load_platform"]
