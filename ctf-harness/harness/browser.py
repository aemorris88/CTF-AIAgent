"""Adapter between the team's existing Claude browser tools and the tested BrowserCTF.

This module performs only user-visible UI actions. It never fetches challenge
JSON or uses locally stored answer hashes to grade submissions.
"""
from __future__ import annotations

from .platform.browser_ctf import BrowserCTF
import re
import uuid
from pathlib import Path


class CTFBrowser:
    def __init__(self):
        self.controller = BrowserCTF()

    def start(self):
        self.controller.start()
        print("Log into the CTF and navigate to the challenge list in the opened browser.")
        input("Press Enter here when the challenge list is visible...")

    def read_page(self) -> str:
        data = self.controller.read_page()
        return f"URL: {data['url']}\nPAGE: {data['title']}\nVISIBLE TEXT:\n{data['visible_text']}"

    def click_text(self, text: str) -> str:
        try:
            data = self.controller.click_text(text)
            return (f"Clicked: {text}\nURL: {data['url']}\n"
                    f"VISIBLE TEXT:\n{data['visible_text']}")
        except Exception as exc:
            return f"CLICK FAILED: {type(exc).__name__}: {str(exc)[:350]}"

    def list_attachments(self) -> list[dict[str, str]]:
        """Only visible same-site challenge resource links are returned."""
        return self.controller.list_attachments()

    def download_to_sandbox(self, label: str, sandbox) -> dict:
        """Download through browser and stage into the existing offline sandbox.

        This copies the attachment but never executes it. BrowserCTF validates
        the exact visible link and restricts downloads to the CTF /assets/ path.
        """
        data = self.controller.download_attachment(label)
        local_file = Path(data["path"])
        if not local_file.is_file():
            raise FileNotFoundError("Browser did not save the attachment")
        # Use a fresh, safe basename. Never let browser-supplied names contain paths.
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(data["filename"]).name).strip(".") or "attachment.bin"
        sandbox_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
        dest = sandbox.put_file(str(local_file), sandbox_name)
        return {
            "filename": safe_name,
            "sandbox_path": dest,
            "bytes": local_file.stat().st_size,
        }

    def submit_flag(self, flag: str) -> dict:
        """Real submission; call only when the instructor permits test attempts."""
        return self.controller.submit_flag(flag)

    def close(self):
        self.controller.close()
