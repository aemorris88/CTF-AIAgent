# FGCU Talon CTF — multi-challenge browser mode

This is a **website-first** queue and results logger. It does not fetch `/data/challenges.json`, does not inspect answer hashes, and never grades flags locally. The authenticated Playwright browser is reused across all challenges; a fresh offline Docker sandbox and a fresh `CTFAgent` instance are started for each challenge.

## Copy these files into your Git-connected `ctf-harness` folder

- `harness/browser_queue.py` — NEW; parses visible dashboard cards and tracks per-challenge events
- `harness/orchestrator.py` — UPDATE (compare with your current branch first; do not overwrite teammate work blindly)
- `test_multichallenge_browser.py` — NEW offline tests
- `test_browser_mode_orchestrator.py` — UPDATE existing browser-mode test for the new workflow
- `apply_agent_multichallenge_prompt.py` — NEW one-time helper to adjust your *existing* `harness/agent.py` (does not replace the file)

The existing `harness/browser.py`, `harness/platform/browser_ctf.py`, sandbox, `.env`, and `config.yaml` are **not** replaced by this patch. Keep your tested `classify_submission_feedback()` fix.

## Apply and test (no Claude calls)

From PowerShell inside `ctf-harness`:

```
python apply_agent_multichallenge_prompt.py
python -m compileall harness
python -m unittest -v test_multichallenge_browser test_browser_mode_orchestrator
python -m unittest -v test_submission_feedback test_browser_download_dispatch
python test_browser_flag_dispatch.py
```

Only run tests you already have installed. If the prompt helper reports it cannot find the expected string, stop and compare your current `agent.py` manually; **do not overwrite it**. The helper saves `harness/agent.py.before_multichallenge` as a backup; never commit that backup.

## Browser-mode live test (requires instructor permission for actual flag submissions)

Begin with TWO challenges, with category filter removed:

```
$env:CTF_BROWSER_MODE="1"
python run.py --max-challenges 2 --categories
```

`--categories` with no category names clears the original `Cryptography` filter. Leave the browser on the dashboard after signing in. Claude will receive a single assigned challenge title each time, but must click that visible title itself, analyze it and submit through the website. The orchestrator then returns to the dashboard via its visible Back control and moves to the next challenge. Each challenge gets a **new sandbox and reasoning context**.

When ready for the full platform, explicitly run:

```
$env:CTF_BROWSER_MODE="1"
python run.py --max-challenges 31 --categories
```

The orchestrator also accepts an optional `run.browser_run_max_seconds` in `config.yaml` (default **3600**). Existing `run.max_steps` and `run.max_wall_seconds` apply **per challenge**; 31 challenges could consume substantial Claude API credits. Check your team's budget, permissions, and rate limits before using 31. Stop with Ctrl+C if necessary. The current code is sequential and does **not** automatically resume an interrupted run. If the page reports a challenge already solved when the dashboard is read initially, that challenge is skipped. Use a dedicated authorized test account for comparable measurements.

## Results

Two CSV files are generated under `results/`:

1. `run-...csv`: the team's existing `RunLogger` row for **each challenge**, including token counts and final outcome.
2. `run-...-per-challenge.csv`: ID, title, category, points, solved, **attempts (tool requests)**, agent steps, agent wall time, **approximate challenge time** (time between confirmed browser click and last submission, or agent stop), token counts, failure reason, and a timing definition.

Each challenge has its own JSONL trace: `logs/<run-id>/challenge-<id>.jsonl`.

**Measurement caution:** `agent_wall_seconds` includes the agent's calls for the assigned challenge. `challenge_seconds` is a host-side approximation and **is not necessarily equivalent** to the platform timer that students saw. Attempt count measures requests through the AI submit tool, not an independently audited server-side count. For rigorous comparison, specify a common timing protocol and consider adding direct UI timer/attempt counter capture. The source program's cost column remains a placeholder while `price_per_mtok_*` are zero.

**Limitations:** Browser selectors rely on the current TalonCTF visible dashboard and `← Back` control; update them if the site changes. A challenge not completed within its per-challenge limit is recorded as unsolved and the runner moves on. The AI may occasionally fail to open its target challenge; inspect the per-challenge JSONL before interpreting that row. Only one flag should be submitted per challenge on controlled early tests; review your `agent.py` submission guard. This package was tested offline with mocked agent, browser, and sandbox; a real 31-challenge run has **not** been performed.

## Git hygiene

Do not add `.env`, browser cookies, `browser_artifacts/`, screenshots containing account data, Docker binaries, generated CSV/logs, or the prompt-helper backup to Git. Stage only the source files listed above. Preserve your separate `sandbox/Dockerfile` modification for teammate review.
