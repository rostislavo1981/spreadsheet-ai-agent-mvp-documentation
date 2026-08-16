"""Prompt-injection / out-of-contract detection (SECURITY_GUARDRAILS §9, ROADMAP §5).

Defense-in-depth: the backend never executes model text as code, but we also
reject plans that try to expand their authority (e.g. instruct the client to
ignore prior rules, or claim system/developer身份). Fail-closed.
"""
from __future__ import annotations

import re

# Patterns that indicate an attempt to subvert the agent contract.
_INJECTION_PATTERNS = [
    re.compile(r"ignore (all|previous|prior|above) (instructions|rules|system)", re.IGNORECASE),
    re.compile(r"disregard (the|your|previous|above)", re.IGNORECASE),
    re.compile(r"you are now", re.IGNORECASE),
    re.compile(r"system prompt", re.IGNORECASE),
    re.compile(r"developer mode", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"reveal (your|the) (prompt|system|instructions)", re.IGNORECASE),
    re.compile(r"execute (this|the following) (code|script|command)", re.IGNORECASE),
    re.compile(r"run (this|the following) (code|script|command)", re.IGNORECASE),
]


def detect_injection(text: str) -> list[str]:
    """Return list of matched injection markers (empty == clean)."""
    if not text:
        return []
    hits = []
    for pat in _INJECTION_PATTERNS:
        if pat.search(text):
            hits.append(pat.pattern)
    return hits


def scan_plan_text(*texts: str) -> list[str]:
    hits: list[str] = []
    for t in texts:
        hits.extend(detect_injection(t))
    # dedupe preserving order
    seen = set()
    out = []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out
