"""Offline regression test. No Claude, Docker or live submissions."""
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from harness.browser_queue import discover_challenges, ChallengeMetrics
from harness import orchestrator
from harness.agent import AgentResult

DASH = '''Skip to main content
ACCESS GRANTED
CRYPTOGRAPHY
#001
Base Case
100 pts
● ○ ○ ○ ○
Unsolved
CRYPTOGRAPHY
#002
Crypto 101
200 pts
● ○ ○ ○ ○
Unsolved
FORENSICS
#014
Unknown File
200 pts
● ○ ○ ○ ○
Unsolved
'''

class FakeBrowser:
    def __init__(self):
        self.controller = self
        self.page = DASH
        self.closed = False
    def start(self): pass
    def read_page(self, max_chars=50000): return {'visible_text': self.page}
    def click_text(self, label):
        if label == '← Back': self.page = DASH
        return 'Clicked: ' + label
    def close(self): self.closed = True

class FakeSandbox:
    def __init__(self, cfg): pass
    def start(self): pass
    def stop(self): pass

class FakeAgent:
    titles = []
    def __init__(self, **kwargs):
        self.kw = kwargs
        self.ch = kwargs['challenge']
    def run(self):
        FakeAgent.titles.append(self.ch.name)
        self.kw['on_event']('observation', {'text': f'Clicked: {self.ch.name}\nURL: dashboard'})
        self.kw['on_event']('action', {'tool': 'submit_flag', 'flag': 'FGCU{fake}'})
        return AgentResult(self.ch.id, self.ch.name, self.ch.category, solved=True,
                           flag='FGCU{fake}', steps=3, wall_seconds=2.5,
                           input_tokens=100, output_tokens=20, submissions=['FGCU{fake}'])

class MultiBrowserTests(unittest.TestCase):
    def test_parse_visible_dashboard(self):
        rows = discover_challenges(DASH)
        self.assertEqual([x.id for x in rows], ['001','002','014'])
        self.assertEqual(rows[2].category, 'Forensics')
        self.assertEqual(rows[1].value, 200)

    def test_solved_cards_skipped(self):
        text = DASH.replace('Base Case\n100 pts\n● ○ ○ ○ ○\nUnsolved', 'Base Case\n100 pts\n● ○ ○ ○ ○\nSolved')
        self.assertEqual([x.id for x in discover_challenges(text)], ['002','014'])

    def test_distinct_csv_rows_without_json_adapter(self):
        FakeAgent.titles.clear()
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(orchestrator, 'CTFAgent', FakeAgent), \
                 patch.object(orchestrator, 'Sandbox', FakeSandbox), \
                 patch('harness.browser.CTFBrowser', FakeBrowser), \
                 patch.object(orchestrator, 'load_platform', side_effect=AssertionError('JSON adapter used')):
                from harness.logging_utils import RunLogger
                import os
                cwd = os.getcwd()
                try:
                    os.chdir(temp)
                    logger = RunLogger('results', 'logs', 'multi-offline-test')
                    cfg = {'run': {'model':'fake', 'max_steps':8, 'max_wall_seconds':60,
                                   'max_challenges': 3, 'categories': []},
                           'flag': {'regex': r'FGCU\{[^}]+\}'}, 'sandbox': {'image': 'fake'}}
                    orchestrator._run_browser_session(cfg, object(), logger)
                    with open('results/multi-offline-test-per-challenge.csv', newline='') as file:
                        rows = list(csv.DictReader(file))
                finally:
                    os.chdir(cwd)
        self.assertEqual(len(rows), 3)
        self.assertEqual([r['challenge_id'] for r in rows], ['001','002','014'])
        self.assertEqual([r['attempts'] for r in rows], ['1','1','1'])
        self.assertEqual(FakeAgent.titles, ['Base Case', 'Crypto 101','Unknown File'])
        self.assertTrue(all(r['challenge_seconds'] for r in rows))

if __name__ == '__main__': unittest.main()
