"""
The orchestrator: the top-level harness loop.

For each selected challenge it spins up a fresh isolated sandbox, stages the
challenge files, runs the agent under a budget, records the result, and tears
the sandbox down. This is the "harness" your project is really about.
"""
from __future__ import annotations

import os
import tempfile
from typing import Any

from .agent import CTFAgent
from .logging_utils import RunLogger
from .platform.base import Challenge, load_platform
from .sandbox import Sandbox


def select_challenges(challenges: list[Challenge], run_cfg: dict) -> list[Challenge]:
    cats = run_cfg.get("categories")
    out = challenges
    if cats:
        cats = {c.lower() for c in cats}
        out = [c for c in out if c.category.lower() in cats]
    limit = run_cfg.get("max_challenges")
    if limit:
        out = out[: int(limit)]
    return out


def _stage_files(platform: Any, ch: Challenge, sandbox: Sandbox, tmp: str) -> None:
    for url in ch.files:
        name = url.split("/")[-1].split("?")[0] or "file"
        local = os.path.join(tmp, name)
        try:
            platform.download_file(url, local)
            sandbox.put_file(local, name)
            print(f"    staged {name}")
        except Exception as exc:  # noqa: BLE001 - keep going, log the miss
            print(f"    [warn] could not stage {url}: {exc}")


def run(cfg: dict, secrets: dict, client: Any, run_id: str | None = None) -> str:
    run_cfg = cfg["run"]
    logger = RunLogger("results", "logs", run_id)
    print(f"Run: {logger.run_id}")

    if os.environ.get("CTF_BROWSER_MODE") == "1":
        return _run_browser_session(cfg, client, logger)

    platform = load_platform(cfg, secrets)
    print("Logging in to platform…")
    platform.login()

    print("Fetching challenge list…")
    challenges = platform.list_challenges()
    chosen = select_challenges(challenges, run_cfg)
    print(f"{len(challenges)} challenges available; attempting {len(chosen)}.\n")

    solved = 0
    for i, ch in enumerate(chosen, 1):
        print(f"[{i}/{len(chosen)}] {ch.short()}")
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Sandbox(cfg)
            try:
                sandbox.start()
                _stage_files(platform, ch, sandbox, tmp)
                agent = CTFAgent(
                    client=client,
                    model=run_cfg["model"],
                    sandbox=sandbox,
                    platform=platform,
                    challenge=ch,
                    flag_regex=cfg["flag"]["regex"],
                    max_steps=int(run_cfg["max_steps"]),
                    max_wall_seconds=int(run_cfg["max_wall_seconds"]),
                    on_event=logger.event_sink(ch.id),
                )
                result = agent.run()
            finally:
                sandbox.stop()

        logger.write_result(
            result,
            float(run_cfg.get("price_per_mtok_input", 0) or 0),
            float(run_cfg.get("price_per_mtok_output", 0) or 0),
        )
        status = "SOLVED" if result.solved else f"unsolved ({result.failure_reason})"
        solved += int(result.solved)
        print(f"    => {status}  [{result.steps} steps, {result.wall_seconds}s, "
              f"{result.input_tokens + result.output_tokens} tok]\n")

    print(f"Done. Solved {solved}/{len(chosen)}. Results: {logger.csv_path}")
    return logger.csv_path


def _run_browser_session(cfg: dict, client: Any, logger: RunLogger) -> str:
    """Website-first sequential challenge run with per-challenge isolation/logs.

    The agent chooses the browser actions for each assigned challenge; only
    the queue metadata originates from visible dashboard text, never JSON.
    """
    from .browser import CTFBrowser
    from .browser_queue import discover_challenges, ChallengeMetrics, write_challenge_metrics

    run_cfg = cfg["run"]
    browser = CTFBrowser()
    metrics_path = os.path.join("results", f"{logger.run_id}-per-challenge.csv")
    completed = 0
    attempted = 0
    import time
    started = time.monotonic()
    total_budget = int(run_cfg.get("browser_run_max_seconds", 3600))
    try:
        browser.start()  # Human signs in once. Browser session persists.
        initial_text = browser.controller.read_page(max_chars=50000)["visible_text"]
        challenges = discover_challenges(initial_text)
        categories = run_cfg.get("categories")
        if categories:
            wanted = {str(x).lower() for x in categories}
            challenges = [c for c in challenges if c.category.lower() in wanted]
        limit = run_cfg.get("max_challenges")
        if limit is not None:
            challenges = challenges[:max(0, int(limit))]
        print(f"Browser discovered {len(challenges)} unsolved challenges in selected run.")
        if not challenges:
            return logger.csv_path

        for index, ch in enumerate(challenges, 1):
            if time.monotonic() - started >= total_budget:
                print(f"Global browser-run time budget reached ({total_budget}s). Stopping.")
                break
            print(f"[{index}/{len(challenges)}] {ch.short()}")
            # Return via visible UI, never via JSON or internal app state.
            before = browser.controller.read_page(max_chars=50000)["visible_text"]
            if "← Back" in before:
                browser.click_text("← Back")
            dashboard = browser.controller.read_page(max_chars=50000)["visible_text"]
            present = {x.id for x in discover_challenges(dashboard, include_solved=True)}
            if ch.id not in present:
                raise RuntimeError(f"Challenge {ch.id} missing from dashboard")
            # Sandbox is fresh and offline for every challenge.
            sandbox = Sandbox(cfg)
            result = None
            sink = logger.event_sink(ch.id)
            record = ChallengeMetrics(ch, sink)
            try:
                sandbox.start()
                agent = CTFAgent(
                    client=client, model=run_cfg["model"], sandbox=sandbox,
                    platform=None, challenge=ch, flag_regex=cfg["flag"]["regex"],
                    max_steps=int(run_cfg["max_steps"]),
                    max_wall_seconds=int(run_cfg["max_wall_seconds"]),
                    on_event=record.event, browser=browser,
                )
                result = agent.run()
            except Exception as exc:
                # Keep the challenge's failed result rather than corrupt other rows.
                from .agent import AgentResult
                result = AgentResult(ch.id, ch.name, ch.category,
                                     failure_reason=f"exception: {type(exc).__name__}: {str(exc)[:120]}")
                sink("error", {"text": result.failure_reason})
            finally:
                sandbox.stop()
            logger.write_result(result,
                float(run_cfg.get("price_per_mtok_input", 0) or 0),
                float(run_cfg.get("price_per_mtok_output", 0) or 0))
            write_challenge_metrics(metrics_path, logger.run_id, ch, result, record)
            completed += int(result.solved)
            attempted += 1
            print(f"    => solved={result.solved} steps={result.steps} "
                  f"attempts={record.attempts} challenge_seconds={record.seconds()}")

        print(f"Done: {completed}/{attempted} solved. Per-challenge results: {metrics_path}")
        return logger.csv_path
    finally:
        browser.close()
