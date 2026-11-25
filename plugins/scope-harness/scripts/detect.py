#!/usr/bin/env python3
"""UserPromptSubmit hook: score a prompt for vagueness with no model call.

Prints one JSON object with additionalContext when the score reaches the
threshold; otherwise prints nothing. Never blocks a prompt and always exits 0.

Usage:
  hook:  stdin = hook JSON (field "prompt")
  debug: python3 detect.py --score "some prompt"
"""
import json
import os
import re
import sys

DEFAULT_THRESHOLD = 5

OPEN_PHRASES = [
    r"\bimprove\b", r"\boptimi[sz]e\b", r"\bbest\b", r"\bbetter\b", r"\bhelp( me)?( with)?\b",
    r"\blook into\b", r"\bsomething\b", r"\bideas?\b", r"\bhow should\b", r"\bwhat do you think\b",
    r"\bany (suggestions|thoughts|tips)\b", r"\bmake it\b", r"\bclean ?up\b", r"\brefactor\b",
    r"\bbrainstorm\b", r"\bexplore\b", r"\bfigure out\b", r"\bwork on\b", r"\bset ?up\b",
    r"\bstuff\b", r"\bthings?\b", r"\bnicer\b", r"\bmodern(ize)?\b", r"\boverall\b",
]

DELIVERABLE_NOUNS = [
    "pr", "pull request", "test", "tests", "doc", "document", "list", "table", "function", "script",
    "file", "report", "summary", "email", "plan", "diagram", "endpoint", "page", "readme", "commit",
    "class", "component", "migration", "query", "chart", "spec", "answer", "example", "regex",
    "command", "config", "schema", "api", "cli", "bug", "error", "issue", "deck", "slide",
    "post", "article", "essay", "outline", "notes", "review", "roadmap", "translation",
    # verbs that imply their own deliverable
    "summarize", "summarise", "translate", "explain", "rename", "draft", "list", "compare",
]

CRITERIA_PATTERNS = [
    r"\bshould\b", r"\bmust\b", r"\bso that\b", r"\buntil\b", r"\bpass(es|ing)?\b", r"\breturns?\b",
    r"\bat most\b", r"\bat least\b", r"\bunder\b", r"\bwithin\b", r"\bexactly\b", r"\bwithout\b",
    r"\bonly\b", r"\bdone when\b", r"\binstead of\b", r"\d",
]

ANCHOR_PATTERNS = [
    r"[\w./-]+\.(py|js|ts|tsx|jsx|go|rs|java|rb|md|json|ya?ml|toml|sql|sh|css|html|c|cpp|h|kt|swift)\b",
    r"https?://", r"`[^`]+`", r"\b\w+\(\)", r"\b[a-z]+_[a-z_]+\b", r"\b[A-Z][a-z]+[A-Z]\w*\b",
    r"\"[^\"]{3,}\"", r"'[^']{3,}'", r"(^|\s)[./~][\w./-]+", r"#\d+",
    r"\b(above|below|attached|pasted|this (file|function|error|diff|page))\b",
]

FOLLOW_UPS = {
    "yes", "no", "ok", "okay", "go", "continue", "thanks", "thank you", "sure", "do it", "next",
    "proceed", "looks good", "lgtm", "stop", "retry", "again", "y", "n",
}


def _has(patterns, text, flags=re.IGNORECASE):
    return any(re.search(p, text, flags) for p in patterns)


def should_skip(prompt):
    stripped = prompt.strip()
    if not stripped:
        return True
    if stripped.startswith(("!raw", "/", "#")):
        return True
    if "## Task brief" in stripped:
        return True
    if stripped.lower().rstrip(".!?") in FOLLOW_UPS:
        return True
    return False


def score(prompt):
    """Return (score 0-10, list of reasons)."""
    text = prompt.strip()
    low = text.lower()
    words = re.findall(r"\w+", low)
    n = len(words)
    reasons = []
    s = 0

    anchored = _has(ANCHOR_PATTERNS, text, 0)  # case matters for CamelCase

    opens = sum(1 for p in OPEN_PHRASES if re.search(p, low))
    if opens:
        s += 2 if opens > 1 else 1
        reasons.append("open-ended wording")

    if not anchored:
        s += 2
        reasons.append("no concrete file, symbol or link")

    if not any(re.search(r"\b" + re.escape(w) + r"\b", low) for w in DELIVERABLE_NOUNS):
        s += 2
        reasons.append("no deliverable named")

    if not _has(CRITERIA_PATTERNS, low):
        s += 1
        reasons.append("no done criteria")

    if n < 6:
        s += 2
        reasons.append("very short")
    elif n <= 12:
        s += 1
        reasons.append("short")
    elif n > 150 and "?" not in text and not re.search(r"^\s*([-*]|\d+\.)\s", text, re.M):
        s += 1
        reasons.append("long with no clear ask")

    if re.match(r"^(fix|change|update|do|improve|check)\s+(it|this|that)\b", low) and not anchored:
        s += 1
        reasons.append("unclear reference (it/this/that)")

    return min(10, s), reasons


def threshold():
    raw = os.environ.get("CLAUDE_PLUGIN_OPTION_THRESHOLD", "")
    try:
        return float(raw) if raw else DEFAULT_THRESHOLD
    except ValueError:
        return DEFAULT_THRESHOLD


def extract_prompt(data):
    for key in ("prompt", "user_prompt", "message"):
        val = data.get(key)
        if isinstance(val, str):
            return val
    return ""


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--score":
        sc, why = score(" ".join(sys.argv[2:]))
        print(json.dumps({"score": sc, "reasons": why}))
        return 0

    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    debug_path = os.environ.get("SCOPE_HARNESS_DEBUG")
    if debug_path:
        try:
            with open(debug_path, "a") as fh:
                fh.write(json.dumps(data) + "\n")
        except OSError:
            pass

    prompt = extract_prompt(data)
    if should_skip(prompt):
        return 0

    sc, why = score(prompt)
    if sc < threshold():
        return 0

    mode = os.environ.get("CLAUDE_PLUGIN_OPTION_MODE", "auto") or "auto"
    context = (
        f"[scope-harness] This request looks open-ended (score {sc}/10: {', '.join(why)}). "
        f"Before starting, use the scope-harness:sharpen skill to write a task brief "
        f"and routing recommendation (mode: {mode}). Skip this if the user already "
        f"gave enough detail in earlier messages."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
