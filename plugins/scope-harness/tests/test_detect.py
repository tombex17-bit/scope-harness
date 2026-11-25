"""Run: python3 -I tests/test_detect.py  (from the plugin folder)"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DETECT = os.path.join(HERE, "..", "scripts", "detect.py")
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import detect  # noqa: E402

def run_hook(prompt, env=None):
    e = dict(os.environ, **(env or {}))
    out = subprocess.run([sys.executable, DETECT], input=json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": prompt}),
                         capture_output=True, text=True, env=e)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()

fails = 0
for line in open(os.path.join(HERE, "prompts.jsonl")):
    case = json.loads(line)
    sc, why = detect.score(case["prompt"])
    flagged = sc >= detect.DEFAULT_THRESHOLD
    ok = flagged == case["vague"]
    fails += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {sc:>2} {case['prompt'][:60]!r} {why}")

# hook protocol checks
out = run_hook("make it better")
data = json.loads(out)
assert data["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
assert "sharpen" in data["hookSpecificOutput"]["additionalContext"]
assert run_hook("Rename `a` to `b` in x.py") == ""
assert run_hook("!raw make it better") == ""
assert run_hook("/model sonnet") == ""
assert run_hook("ok") == ""
assert run_hook("make it better", {"CLAUDE_PLUGIN_OPTION_THRESHOLD": "10"}) == ""
print(f"\n{fails} classification failures; hook protocol checks passed")
sys.exit(1 if fails else 0)
