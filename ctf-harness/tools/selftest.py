#!/usr/bin/env python3
"""
Offline self-test: exercises the full harness wiring WITHOUT Docker, an API key,
or the live site. Uses a fake HTTP session (static challenges.json shape), a fake
Claude client, and a fake sandbox. Run from the repo root:

    python tools/selftest.py
"""
from __future__ import annotations

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.agent import CTFAgent                      # noqa: E402
from harness.flags import find_flags                    # noqa: E402
from harness.platform.azure_swa import AzureStaticWebAppPlatform  # noqa: E402
from harness.platform.base import load_platform         # noqa: E402

FLAG = "FGCU{mock_pipeline_works}"


# --- tiny fakes -------------------------------------------------------------
class _Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Usage:
    def __init__(self, i, o):
        self.input_tokens, self.output_tokens = i, o


class _Resp:
    def __init__(self, content, stop_reason, usage):
        self.content, self.stop_reason, self.usage = content, stop_reason, usage


class FakeClient:
    """Plays: step1 -> run `echo FLAG`; step2 -> submit the flag it 'saw'."""
    def __init__(self):
        self.messages = self
        self._step = 0

    def create(self, **kw):
        self._step += 1
        if self._step == 1:
            return _Resp(
                [_Block(type="text", text="Looking."),
                 _Block(type="tool_use", id="t1", name="run_command",
                        input={"command": f"echo {FLAG}"})],
                "tool_use", _Usage(100, 20),
            )
        return _Resp(
            [_Block(type="tool_use", id="t2", name="submit_flag",
                    input={"flag": FLAG})],
            "tool_use", _Usage(120, 10),
        )


class FakeSandbox:
    def exec(self, command, timeout=None):
        return (0, command[5:] + "\n") if command.startswith("echo ") else (0, "")


class FakeHTTPResp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


class FakeSession:
    def __init__(self, payload):
        self.headers: dict = {}
        self._payload = payload

    def get(self, url, **kw):
        return FakeHTTPResp(self._payload)


def check(label, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        raise SystemExit(1)


ADAPTER_CFG = {
    "platform": {
        "adapter": "azure_swa",
        "base_url": "https://site.example",
        "auth": {"mode": "none"},
        "challenges": {
            "list_path": "/data/challenges.json",
            "files_base_url": None,
            "field_map": {
                "id": "id", "name": "title", "category": "categoryLabel",
                "description": "description", "value": "points",
                "files": "resources", "answer_sha256": "flagSha256",
            },
        },
        "submit": {"mode": "local_hash"},
    }
}


def main():
    answer = "FGCU{static_site_ok}"
    digest = hashlib.sha256(answer.encode()).hexdigest()
    payload = {"version": 1, "challenges": [{
        "id": "001", "title": "Base Case", "category": "crypto",
        "categoryLabel": "Cryptography", "points": 100, "flagSha256": digest,
        "description": "decode it", "resources": [
            {"href": "assets/x.png", "download": "x.png"},
            {"href": "https://third-party/api", "external": True},  # must be skipped
        ],
    }]}

    print("1. flag regex")
    check("find_flags extracts", find_flags(f"x {FLAG} y", r"FGCU\{[^}]+\}") == [FLAG])

    print("2. static adapter: list + field mapping + file resolution")
    plat = AzureStaticWebAppPlatform(ADAPTER_CFG, {})
    plat.session = FakeSession(payload)
    chs = plat.list_challenges()
    check("one challenge parsed", len(chs) == 1)
    c = chs[0]
    check("title -> name", c.name == "Base Case")
    check("categoryLabel -> category", c.category == "Cryptography")
    check("points -> value", c.value == 100)
    check("flagSha256 captured", c.answer_sha256 == digest)
    check("external resource skipped, local kept",
          c.files == ["https://site.example/assets/x.png"])

    print("3. local SHA-256 grading")
    check("correct flag accepted", plat.submit_flag(c, answer) is True)
    check("wrong flag rejected", plat.submit_flag(c, "FGCU{nope}") is False)
    check("whitespace tolerated", plat.submit_flag(c, f"  {answer}  ") is True)

    print("4. mock platform + full agent loop")
    mock = load_platform({"platform": {"adapter": "mock"}}, {})
    mch = mock.list_challenges()[0]
    agent = CTFAgent(
        client=FakeClient(), model="fake", sandbox=FakeSandbox(), platform=mock,
        challenge=mch, flag_regex=r"FGCU\{[^}]+\}", max_steps=10,
        max_wall_seconds=60, on_event=None,
    )
    res = agent.run()
    check("agent solved", res.solved is True)
    check("flag captured", res.flag == FLAG)
    check("two steps", res.steps == 2)
    check("tokens summed", res.input_tokens == 220 and res.output_tokens == 30)

    print("\nAll self-tests passed.")


if __name__ == "__main__":
    main()
