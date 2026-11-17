# CTF Agent Harness

A small, legible harness that points a Claude-powered agent at a live CTF
platform, lets it solve challenges inside an isolated sandbox with **no access to
outside materials**, and logs the results.

Built for an authorized class project: testing/improving your own CTF platform.
Only run it against a platform you're permitted to test.

## What's what

Two layers, cleanly separated:

| Layer | File(s) | Role |
|-------|---------|------|
| **Agent** | `harness/agent.py` | Minimal ReAct loop (thought → action → observation) over Claude's tool-use API. Three tools: `run_command`, `submit_flag`, `give_up`. |
| **Harness** | `harness/orchestrator.py`, `sandbox.py`, `platform/`, `logging_utils.py` | Pulls challenges from the site, runs each agent in a throwaway sandbox under a budget, submits flags, logs everything. |

The harness is the interesting part: existing CTF agents assume challenges are
local files; yours live on a website, so the harness is the adapter + sandbox +
isolation + scoring around a reusable agent loop.

```
run.py ─ orchestrator ─┬─ platform adapter  (login, list, download, submit flag)
                       ├─ sandbox           (Docker box the agent runs commands in)
                       ├─ agent             (Claude ReAct loop)
                       └─ logger            (per-challenge transcript + results.csv)
```

## Prerequisites

- **Docker** (Desktop on your Mac is fine) — runs the sandbox.
- **Python 3.11+**.
- An **Anthropic API key**.
- Your **CTF platform login**.

> Run this on your own machine or a lab VM. It needs Docker plus network access
> to your CTF platform, so it can't run inside a cloud chat sandbox.

## Setup

```bash
# 1. deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. secrets
cp .env.example .env        # then edit: ANTHROPIC_API_KEY, CTF_USERNAME, CTF_PASSWORD

# 3. build the sandbox image (one time, ~a few minutes)
docker build -t ctf-harness-sandbox:latest sandbox/
```

## Point it at your platform

Already configured for the FGCU static site in `config.yaml`. That platform
serves its challenges as a static file (`/data/challenges.json`) and grades
flags client-side with SHA-256, so the harness needs **no login**: it fetches
the list directly and grades locally by hashing the agent's answer. If your
site later gates those files behind the GitHub sign-in, set `auth.mode:
cookie_env` and put your browser Cookie header value in `.env` as `CTF_COOKIE`.

Verify without spending anything:

```bash
python run.py --dry-run        # fetches + lists the real challenges, runs no agent
```

When that prints the 31-challenge list, the adapter is working.

## Run some test runs

```bash
# attempt the first few challenges (counts/filters come from config.yaml)
python run.py

# a focused test
python run.py --max-challenges 2 --categories crypto forensics

# one specific challenge by id
python run.py --challenge 7
```

Start small: `max_steps: 15`, two or three easy challenges, one model. Confirm
the pipeline end-to-end before scaling up.

## The "no outside materials" guarantee

Grading is done locally by the harness (SHA-256), so the agent's sandbox never
needs network access to be scored — which makes the isolation airtight for this
platform. Enforced two ways at once:

1. **No retrieval tool.** The agent only has `run_command`, `submit_flag`,
   `give_up`. It can't search the web or fetch write-ups.
2. **Network isolation** (`config.yaml → sandbox.network_mode`):
   - `none` — fully offline. A hard guarantee; best for file-based challenges
     (crypto / rev / forensics / most misc). **Recommended default.**
   - `isolated` — an internal Docker network: reaches only other containers you
     attach (e.g. a locally-run copy of a pwn/web service), never the internet.
   - `host` — unrestricted; only for a remote service you must reach, at the cost
     of weaker isolation.

**Honest caveat for your report:** the LLM inference call itself still goes to
Anthropic — "no outside materials" means the *agent's tools* can't fetch
solutions at solve-time, not that the model is air-gapped. A true air-gap needs a
local open-weights model. And "reach remote service X but nothing else" is an
OS-firewall concern (iptables/ufw egress allowlist) beyond Docker's basic
networking; for a clean experiment, prefer file-based challenges with
`network_mode: none`, or run the vulnerable service locally on the `isolated`
network.

## Output

- `results/<run-id>.csv` — one row per challenge: solved?, steps, wall-time,
  input/output tokens, estimated cost, submissions, failure reason. **This is your
  results table.**
- `logs/<run-id>/challenge-<id>.jsonl` — full transcript (every thought, command,
  observation, submission) for debugging and your appendix.

Set `price_per_mtok_input/output` in `config.yaml` to get the cost column.

## Verify the plumbing (no Docker / key / site needed)

```bash
python tools/selftest.py       # mock platform + fake client + fake sandbox
```

## Extending

- **New platform** → add a class in `harness/platform/` implementing the four
  `CTFPlatform` methods; register it in `platform/base.py::load_platform`.
- **More agent tools** (e.g. a dedicated `decompile`) → add to `TOOLS` and
  `_dispatch` in `agent.py`.
- **Swap in a published agent** (NYU D-CIPHER, Cybench) → keep this harness's
  platform adapter + logger and call their solver in place of `CTFAgent.run()`.

## Layout

```
ctf-harness/
├─ run.py                  CLI
├─ config.yaml             all site-specific settings
├─ .env.example            secrets template
├─ requirements.txt
├─ harness/
│  ├─ orchestrator.py      the top-level harness loop
│  ├─ agent.py             minimal ReAct agent (Claude tool-use)
│  ├─ sandbox.py           Docker executor + network isolation
│  ├─ flags.py             flag regex detection
│  ├─ logging_utils.py     transcripts + results table
│  └─ platform/
│     ├─ base.py           CTFPlatform interface + Challenge
│     ├─ azure_swa.py      config-driven adapter for your site
│     └─ mock.py           fake platform for testing
├─ sandbox/Dockerfile      the agent's toolbox image
└─ tools/
   ├─ discover_api.md      recipe to map your platform's API
   └─ selftest.py          offline wiring test
```
