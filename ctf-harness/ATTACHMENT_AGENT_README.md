# Agent-controlled attachment handling

This patch exposes `browser_list_attachments` and `browser_download` to the existing
Claude tool loop in browser mode. It uses the user's previously verified
`BrowserCTF.download_attachment` and the existing `Sandbox.put_file`.

**Files to copy into `ctf-harness` on `feature/platform-integration`:**
- `harness/agent.py` (merge if your teammate changed it)
- `harness/browser.py` (merge if your teammate changed it)
- `test_browser_download_dispatch.py`

No changes are needed in `sandbox.py` or `orchestrator.py`.

## Offline test

```powershell
cd "$env:USERPROFILE\Downloads\CTF-AIAgent-Connected\ctf-harness"
python -m unittest -v test_browser_download_dispatch
python -m unittest -v test_browser_mode_orchestrator
python test_browser_flag_dispatch.py
```

The first test uses mocked browser and sandbox objects; it does **not** download
from the real site or make a real submission. A prior live test separately
confirmed download of challenge #014 and transfer into Docker.

## How the AI uses the tools

1. `browser_read` to open a challenge and read instructions.
2. `browser_list_attachments` to find an exact visible resource label.
3. `browser_download` with that label to download via the UI, stage to `/work`.
4. `run_command` to inspect the file in the offline container (e.g. `file /work/...`).
5. `submit_flag` through the website when confident.

## Safety and remaining work

- Only download links visible on the page, from the CTF site's `/assets/` area.
- The downloaded asset is copied into the sandbox but never executed automatically.
- Keep `browser_artifacts/`, `.env`, and any session cookies out of Git.
- Do not change network_mode from `none` for this functionality.
- Some challenges include external links instead of downloadable assets. They are not
  downloaded by this tool and require separate instructor-approved policy.
- Real AI-driven navigation still needs a Claude end-to-end run with approved access,
  permitted test submissions, and accurate performance logging.
- The user modified `sandbox/Dockerfile` to omit unavailable `radare2`; coordinate that
  dependency with the team before merging it.
