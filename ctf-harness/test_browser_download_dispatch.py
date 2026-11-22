"""Offline unit test of agent attachment tools (no API, Docker, website)."""
import tempfile
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import Mock, patch

from harness.agent import CTFAgent, AgentResult, BROWSER_TOOLS
from harness.browser import CTFBrowser
from harness.platform.base import Challenge


class TestBrowserAttachmentDispatch(TestCase):
    def setUp(self):
        self.browser = Mock()
        self.browser.list_attachments.return_value = [{"label": "Download magicinme unknown file", "href": "assets/magicinme"}]
        self.browser.download_to_sandbox.return_value = {
            "filename": "magicinme", "sandbox_path": "/work/abcd1234_magicinme", "bytes": 40640,
        }
        self.sandbox = Mock()
        ch = Challenge(id="browser-session", name="Website-selected challenge", category="browser", description="")
        self.agent = CTFAgent(client=None, model="fake", sandbox=self.sandbox, platform=None,
                             challenge=ch, flag_regex=r"FGCU\{[^}]+\}",
                             max_steps=5, max_wall_seconds=60, browser=self.browser)
        self.result = AgentResult(ch.id, ch.name, ch.category)

    def test_list_and_download(self):
        tool_names = [tool["name"] for tool in BROWSER_TOOLS]
        self.assertIn("browser_download", tool_names)
        self.assertIn("browser_list_attachments", tool_names)
        obs, stop = self.agent._dispatch("browser_list_attachments", {}, self.result)
        self.assertIn("Download magicinme unknown file", obs)
        self.assertFalse(stop)
        obs, stop = self.agent._dispatch("browser_download", {"label": "Download magicinme unknown file"}, self.result)
        self.browser.download_to_sandbox.assert_called_once_with("Download magicinme unknown file", self.sandbox)
        self.assertIn("/work/abcd1234_magicinme", obs)
        self.assertFalse(stop)

    def test_missing_label_does_not_download(self):
        obs, stop = self.agent._dispatch("browser_download", {"label": ""}, self.result)
        self.assertIn("failed", obs.lower())
        self.browser.download_to_sandbox.assert_not_called()
        self.assertFalse(stop)

    def test_real_adapter_uses_sandbox_put_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            item = Path(tmp) / "file.txt"
            item.write_bytes(b"test content")
            adapter = CTFBrowser()
            adapter.controller = Mock()
            adapter.controller.download_attachment.return_value = {
                "filename": "file.txt", "path": str(item), "bytes": 12,
            }
            sandbox = Mock()
            sandbox.put_file.side_effect = lambda local, rel: f"/work/{rel}"
            result = adapter.download_to_sandbox("Download file", sandbox)
            sandbox.put_file.assert_called_once()
            self.assertEqual(sandbox.put_file.call_args.args[0], str(item))
            self.assertTrue(result["sandbox_path"].startswith("/work/"))
            self.assertEqual(result["bytes"], 12)


if __name__ == "__main__":
    main()
