---
name: sharpen
description: Turns a vague or open-ended request into a scoped task brief with done criteria, a budget, and a recommended model and effort level. Use when a request lacks a clear deliverable, scope or finish line, or when the scope-harness hook flags the prompt.
argument-hint: "[the request to sharpen]"
model: haiku
effort: low
allowed-tools: Read, Glob, Grep, Agent, AskUserQuestion
---

# Sharpen a request into a task brief

Your job is to spend a little now so the real work costs less. Produce a brief, then stop.
Do not start the task itself inside this skill.

Request to sharpen: $ARGUMENTS (if empty, use the user's latest message).
Clarification mode: ${user_config.mode} (auto if blank).

## 1. Check whether sharpening is needed

If the request already names a deliverable, its inputs, and how to tell it is done,
write the brief straight away with no questions. Otherwise continue.

## 2. Infer before asking

Fill as many brief fields as you can from what is already available:
- the request itself and the conversation so far
- CLAUDE.md and the project's README
- the repository, for "which files" or "which stack" questions: delegate this to the
  `scope-harness:scoper` agent instead of reading many files yourself

Mark every inferred field as an assumption.

## 3. Ask only what changes the outcome

Ask a question only when the field is still unknown AND a wrong guess would waste
real work. Ask at most 3 questions, in a single AskUserQuestion call, each with
2 to 4 options and a recommended default. Good targets, in priority order:
1. The deliverable (what exactly should exist at the end)
2. Done criteria (how we know it is finished)
3. Scope boundary (what is out of scope)
4. Budget (quick pass vs thorough)

If the user answers "just go", "you decide" or similar, use the defaults and list
them under Assumptions.

Mode rules: `infer` never asks. `ask` asks whenever a key gap remains. `auto` asks
only when the request is broad (several possible deliverables) or hard to undo.

## 4. Write the brief

Use exactly this shape, about 150 words:

## Task brief
**Goal:** one sentence on why this matters
**Deliverable:** the exact artifact
**Inputs:** files, links, prior decisions
**Constraints:** must and must-not rules
**Out of scope:** what not to touch
**Done when:** 2 to 4 checkable criteria
**Budget:** small | medium | large, plus a stop rule
**Assumptions:** inferred, not confirmed

## 5. Route it

Read `${CLAUDE_PLUGIN_ROOT}/skills/sharpen/routing.md` and pick the cheapest model
and effort likely to meet the done criteria on the first attempt. Append:

## Routing
**Task class:** ...
**Recommended:** <haiku|sonnet|opus>, effort <low|medium|high|xhigh>
**Why:** one line
**Escalate if:** the condition that justifies a bigger model
**Run it:** either `/model <m>` + `/effort <e>` to continue here, or
"delegate" to run it in a subagent with that model

Never recommend effort `max` unless the user asked for it.

## 6. Hand back

Show the brief and routing, then ask one thing: "Go, edit, or delegate?"
Once work begins, treat the brief as the contract: stay inside the scope and stop
when the done criteria pass or the stop rule triggers.
