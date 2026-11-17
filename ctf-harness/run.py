#!/usr/bin/env python3
"""
CLI entry point.

  python run.py --dry-run            # log in + list challenges, run nothing
  python run.py                      # attempt challenges per config.yaml
  python run.py --max-challenges 2 --categories crypto forensics
  python run.py --challenge 7        # attempt a single challenge by id
"""
from __future__ import annotations

import argparse
import os
import sys

import yaml
from dotenv import load_dotenv


def load_config(path: str) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def main() -> int:
    ap = argparse.ArgumentParser(description="CTF agent harness")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--dry-run", action="store_true",
                    help="Log in and list challenges, then exit.")
    ap.add_argument("--challenge", help="Attempt only this challenge id.")
    ap.add_argument("--categories", nargs="*", help="Override categories filter.")
    ap.add_argument("--max-challenges", type=int, help="Override challenge count.")
    ap.add_argument("--model", help="Override the model.")
    ap.add_argument("--run-id", help="Name this run (default: timestamp).")
    args = ap.parse_args()

    load_dotenv()
    cfg = load_config(args.config)

    # CLI overrides
    if args.categories is not None:
        cfg["run"]["categories"] = args.categories
    if args.max_challenges is not None:
        cfg["run"]["max_challenges"] = args.max_challenges
    if args.model:
        cfg["run"]["model"] = args.model

    secrets = {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
        "CTF_USERNAME": os.getenv("CTF_USERNAME", ""),
        "CTF_PASSWORD": os.getenv("CTF_PASSWORD", ""),
    }

    # --- dry run: no API key or Docker needed, just exercise the adapter -----
    if args.dry_run:
        from harness.platform.base import load_platform
        platform = load_platform(cfg, secrets)
        platform.login()
        challenges = platform.list_challenges()
        print(f"{len(challenges)} challenges:\n")
        for c in challenges:
            files = f"  files={len(c.files)}" if c.files else ""
            conn = "  [remote]" if c.connection_info else ""
            print(f"  id={c.id:<4} [{c.category}] {c.name}{files}{conn}")
        return 0

    # --- real run -----------------------------------------------------------
    if not secrets["ANTHROPIC_API_KEY"]:
        print("ERROR: set ANTHROPIC_API_KEY in .env", file=sys.stderr)
        return 1

    import anthropic
    from harness import orchestrator

    client = anthropic.Anthropic(api_key=secrets["ANTHROPIC_API_KEY"])

    if args.challenge:
        # Single-challenge mode: filter to just that id.
        cfg["run"]["max_challenges"] = None
        cfg["run"]["categories"] = None
        from harness.platform.base import load_platform
        platform = load_platform(cfg, secrets)
        platform.login()
        wanted = [c for c in platform.list_challenges() if c.id == str(args.challenge)]
        if not wanted:
            print(f"No challenge with id {args.challenge}", file=sys.stderr)
            return 1
        # Reuse orchestrator by monkeypatching the selection to our one challenge.
        import harness.orchestrator as orch
        orch.load_platform = lambda *a, **k: _Preloaded(platform, wanted)  # type: ignore

    orchestrator.run(cfg, secrets, client, run_id=args.run_id)
    return 0


class _Preloaded:
    """Wrap an already-logged-in platform returning a fixed challenge subset."""
    def __init__(self, platform, challenges):
        self._p = platform
        self._ch = challenges

    def login(self):
        return

    def list_challenges(self):
        return self._ch

    def __getattr__(self, name):
        return getattr(self._p, name)


if __name__ == "__main__":
    raise SystemExit(main())
