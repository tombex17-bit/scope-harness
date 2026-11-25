# scope-harness

A Claude Code plugin that turns vague requests into a scoped task brief before any
expensive work starts, then recommends the cheapest model and effort level likely
to get it right on the first try.

## What it does

1. **Detects vague prompts for free.** A `UserPromptSubmit` hook runs a local Python
   script (no model call) that scores each prompt 0 to 10. Clear prompts pass through
   untouched. At or above the threshold (default 5) it adds a one-line nudge.
2. **Sharpens on Haiku.** The `sharpen` skill runs at `model: haiku`, `effort: low`.
   It infers what it can from the conversation and repo, asks at most 3 questions,
   and writes an 8-field brief: goal, deliverable, inputs, constraints, out of scope,
   done criteria, budget with a stop rule, and assumptions.
3. **Routes the work.** It appends a model and effort recommendation from
   `routing.md`, with an escalation condition, and asks: go, edit, or delegate?
4. **Scoper agent.** `scope-harness:scoper` is a read-only Haiku agent that answers
   narrow repo questions so the main thread does not spend tokens exploring.

## Install

From a clone or folder:

```
claude --plugin-dir ./plugins/scope-harness
```

From GitHub, once pushed:

```
/plugin marketplace add <owner>/<repo>
/plugin install scope-harness@scope-harness-marketplace
```

## Use

- It runs automatically on vague prompts.
- Run it by hand: `/scope-harness:sharpen <request>`
- Skip it for one prompt: start the prompt with `!raw`
- Settings (`/plugin` > scope-harness > configure):
  - `mode`: `auto` (default), `ask`, or `infer` (never asks; lists assumptions)
  - `threshold`: 0 to 10, default 5. Raise it for fewer nudges.

## Test the detector

```
cd plugins/scope-harness
python3 -I tests/test_detect.py
python3 scripts/detect.py --score "make it better"
```

Set `SCOPE_HARNESS_DEBUG=/path/file.jsonl` to log the hook input.

## Layout

```
.claude-plugin/marketplace.json
plugins/scope-harness/
  .claude-plugin/plugin.json
  hooks/hooks.json
  scripts/detect.py
  skills/sharpen/SKILL.md
  skills/sharpen/routing.md
  agents/scoper.md
  tests/
```
