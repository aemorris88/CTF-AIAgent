"""Flag detection helpers."""
from __future__ import annotations

import re


def find_flags(text: str, pattern: str) -> list[str]:
    """Return all substrings of `text` matching the platform's flag regex."""
    if not text:
        return []
    return list(dict.fromkeys(re.findall(pattern, text)))  # de-duped, ordered
