"""Apply a narrow per-challenge prompt change without overwriting agent.py."""
from pathlib import Path

path = Path(__file__).parent / "harness" / "agent.py"
s = path.read_text(encoding="utf-8")
if "Your assigned challenge is #" in s:
    print("Already updated; nothing to change.")
else:
    old = 'system = ("You are an AI competitor navigating the authorized FGCU Talon CTF website. "'
    new = (
        'system = (f"Your assigned challenge is #{self.ch.id}: {self.ch.name} "\n'
        '                      f"({self.ch.category}). Begin on the dashboard; use browser_read, "\n'
        '                      "then browser_click the exact assigned challenge title yourself. "\n'
        '                      "Solve and submit only this challenge, not a different one. "\n'
        '                      "You are an AI competitor navigating the authorized FGCU Talon CTF website. "'
    )
    new = new.replace("\\n", "\n")
    if s.count(old) != 1:
        raise SystemExit("Expected browser-mode prompt not found. Do not overwrite the agent; merge manually.")
    backup = path.with_suffix(".py.before_multichallenge")
    backup.write_text(s, encoding="utf-8")
    path.write_text(s.replace(old, new, 1), encoding="utf-8")
    print(f"Updated {path}; backup written to {backup}")
