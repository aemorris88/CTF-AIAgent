"""
Docker-backed sandbox: the isolated box the agent's shell commands run inside.

Design goals:
  * Isolation — the agent executes real tools but can't touch your host.
  * The "no outside materials" guarantee — controlled by network_mode:
        none     -> fully offline (recommended; a hard guarantee for file-based
                    challenges: the agent physically cannot fetch a writeup).
        isolated -> an INTERNAL docker network: reaches only other containers you
                    attach to it (e.g. a locally-run copy of a pwn/web service),
                    never the open internet.
        host     -> unrestricted. Only use if a challenge needs a *remote* service
                    and you accept weaker isolation (see README for pairing this
                    with an OS-level egress allowlist).
Commands run via `docker exec`, so nothing about the host leaks in.
"""
from __future__ import annotations

import subprocess
import uuid
from typing import Any

NETWORK_NAME = "ctf-harness-net"


class SandboxError(RuntimeError):
    pass


def _run(args: list[str], timeout: int | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return 124, "[timed out]"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


class Sandbox:
    def __init__(self, cfg: dict[str, Any]):
        s = cfg["sandbox"]
        self.image = s["image"]
        self.network_mode = s.get("network_mode", "none")
        self.command_timeout = int(s.get("command_timeout", 120))
        self.workdir = s.get("workdir", "/work")
        self.name = f"ctf-sbx-{uuid.uuid4().hex[:8]}"
        self._started = False

    # -- lifecycle -----------------------------------------------------------
    def _net_args(self) -> list[str]:
        if self.network_mode == "none":
            return ["--network", "none"]
        if self.network_mode == "isolated":
            self._ensure_network()
            return ["--network", NETWORK_NAME]
        if self.network_mode == "host":
            return []  # default bridge w/ internet; least isolated
        raise ValueError(f"Unknown network_mode: {self.network_mode!r}")

    def _ensure_network(self) -> None:
        code, _ = _run(["docker", "network", "inspect", NETWORK_NAME])
        if code != 0:
            # --internal => no route to the outside world.
            code, out = _run(
                ["docker", "network", "create", "--internal", NETWORK_NAME]
            )
            if code != 0:
                raise SandboxError(f"Could not create isolated network:\n{out}")

    def start(self) -> None:
        args = [
            "docker", "run", "-d", "--name", self.name,
            "-w", self.workdir,
            *self._net_args(),
            # Let rev/pwn tooling (gdb, ptrace) work inside the box:
            "--cap-add", "SYS_PTRACE", "--security-opt", "seccomp=unconfined",
            # Guardrails:
            "--pids-limit", "512", "--memory", "2g",
            self.image, "sleep", "infinity",
        ]
        code, out = _run(args, timeout=120)
        if code != 0:
            raise SandboxError(
                f"Failed to start sandbox container. Is the image '{self.image}' "
                f"built and is Docker running?\n{out}"
            )
        _run(["docker", "exec", self.name, "mkdir", "-p", self.workdir])
        self._started = True

    def put_file(self, local_path: str, rel_name: str) -> str:
        dest = f"{self.workdir}/{rel_name}"
        code, out = _run(["docker", "cp", local_path, f"{self.name}:{dest}"])
        if code != 0:
            raise SandboxError(f"Failed to copy {local_path} into sandbox:\n{out}")
        return dest

    def exec(self, command: str, timeout: int | None = None) -> tuple[int, str]:
        """Run a shell command inside the sandbox. Returns (exit_code, combined_output)."""
        if not self._started:
            raise SandboxError("Sandbox not started.")
        t = timeout or self.command_timeout
        return _run(
            ["docker", "exec", self.name, "bash", "-lc", command], timeout=t + 5
        )

    def stop(self) -> None:
        if self._started:
            _run(["docker", "rm", "-f", self.name])
            self._started = False

    def __enter__(self) -> "Sandbox":
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()
