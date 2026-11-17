"""
Adapter for the FGCU-style static CTF site.

How this platform actually works (discovered from the live site):
  * Challenges are a static JSON file at /data/challenges.json
    ({"version":1,"challenges":[ ... ]}).
  * Each challenge carries `flagSha256` — the site grades a flag by hashing your
    input in the browser and comparing. So THIS HARNESS GRADES LOCALLY: we
    sha256 the agent's candidate and compare. No submit endpoint, no network,
    no login needed for scoring.
  * Attachments live under /assets/... (from each challenge's `resources`).

Auth: the static files are usually public. If your site gates them behind the
GitHub sign-in, paste the browser Cookie header value into .env as CTF_COOKIE
and set auth.mode: "cookie_env" — it'll be sent on every request.
"""
from __future__ import annotations

import hashlib
import os
from typing import Any
from urllib.parse import urljoin

import requests

from .base import Challenge, CTFPlatform


class AzureStaticWebAppPlatform(CTFPlatform):
    def __init__(self, cfg: dict[str, Any], secrets: dict[str, str]):
        self.cfg = cfg
        self.p = cfg["platform"]
        self.base_url = self.p["base_url"].rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ctf-harness/1.0"})
        # Optional: replay a browser session cookie if the site gates its files.
        if self.p.get("auth", {}).get("mode") == "cookie_env":
            cookie = secrets.get("CTF_COOKIE", "")
            if cookie:
                self.session.headers.update({"Cookie": cookie})

    def _url(self, path: str) -> str:
        if path.startswith("http"):
            return path
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def login(self) -> None:
        # Nothing to do: grading is local and the data file is fetched directly.
        return

    def list_challenges(self) -> list[Challenge]:
        ch_cfg = self.p["challenges"]
        resp = self.session.get(self._url(ch_cfg["list_path"]), timeout=30)
        resp.raise_for_status()
        try:
            raw = resp.json()
        except ValueError:
            raise RuntimeError(
                "Challenge list did not return JSON. If your site gates /data "
                "behind sign-in, set auth.mode: cookie_env and put the browser "
                "Cookie value in .env as CTF_COOKIE."
            )
        items = raw.get("challenges", raw) if isinstance(raw, dict) else raw
        fmap = ch_cfg["field_map"]
        files_base = ch_cfg.get("files_base_url") or self.base_url

        out: list[Challenge] = []
        for item in items:
            files = []
            for r in item.get(fmap.get("files", "resources"), []) or []:
                href = r.get("href") if isinstance(r, dict) else r
                if not href or (isinstance(r, dict) and r.get("external")):
                    continue  # skip external links (e.g. live third-party APIs)
                files.append(href if href.startswith("http")
                             else urljoin(files_base.rstrip("/") + "/", href.lstrip("/")))
            out.append(
                Challenge(
                    id=str(item.get(fmap["id"], "")),
                    name=str(item.get(fmap["name"], "unnamed")),
                    category=str(item.get(fmap["category"], "unknown")),
                    description=str(item.get(fmap["description"], "")),
                    value=item.get(fmap.get("value", "points")),
                    files=files,
                    connection_info=None,
                    answer_sha256=item.get(fmap.get("answer_sha256", "flagSha256")),
                )
            )
        return out

    def download_file(self, url: str, dest_path: str) -> str:
        resp = self.session.get(url, timeout=60, stream=True)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)
        return dest_path

    def submit_flag(self, challenge: Challenge, flag: str) -> bool:
        """Local grading: the platform's own mechanism is sha256(flag) == stored hash."""
        if not challenge.answer_sha256:
            return False
        digest = hashlib.sha256(flag.strip().encode()).hexdigest()
        return digest.lower() == challenge.answer_sha256.lower()
