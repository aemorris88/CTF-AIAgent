"""
Logging: a full JSONL transcript per challenge (for debugging / your appendix)
plus a flat results table (for your report's numbers).
"""
from __future__ import annotations

import csv
import json
import os
import time
from typing import Any, Callable

RESULT_COLUMNS = [
    "run_id", "challenge_id", "challenge_name", "category",
    "solved", "flag", "steps", "wall_seconds",
    "input_tokens", "output_tokens", "est_cost_usd",
    "submissions", "failure_reason",
]


class RunLogger:
    def __init__(self, results_dir: str, logs_dir: str, run_id: str | None = None):
        self.run_id = run_id or time.strftime("run-%Y%m%d-%H%M%S")
        self.results_dir = results_dir
        self.logs_dir = os.path.join(logs_dir, self.run_id)
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        self.csv_path = os.path.join(self.results_dir, f"{self.run_id}.csv")
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="") as fh:
                csv.writer(fh).writerow(RESULT_COLUMNS)

    def event_sink(self, challenge_id: str) -> Callable[[str, dict], None]:
        """Return an on_event callback that appends to this challenge's transcript."""
        path = os.path.join(self.logs_dir, f"challenge-{challenge_id}.jsonl")

        def sink(kind: str, data: dict) -> None:
            rec = {"t": round(time.time(), 2), "kind": kind, **data}
            with open(path, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            # Also echo a short line to the console so you can watch it live.
            preview = data.get("command") or data.get("text") or data.get("flag") or ""
            preview = str(preview).replace("\n", " ")[:100]
            print(f"  · {kind:<11} {preview}")

        return sink

    def write_result(self, result: Any, price_in: float, price_out: float) -> None:
        cost = (
            result.input_tokens / 1_000_000 * price_in
            + result.output_tokens / 1_000_000 * price_out
        )
        row = [
            self.run_id, result.challenge_id, result.challenge_name, result.category,
            result.solved, result.flag or "", result.steps, result.wall_seconds,
            result.input_tokens, result.output_tokens, round(cost, 4),
            " | ".join(result.submissions), result.failure_reason or "",
        ]
        with open(self.csv_path, "a", newline="") as fh:
            csv.writer(fh).writerow(row)
