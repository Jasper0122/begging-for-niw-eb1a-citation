---
name: niw-citation-schedule
description: Set up, verify, repair, or manually trigger Jasper Li's daily NIW/EB-1A citation-outreach scheduled cloud routine (the one that creates Gmail drafts to authors who might cite his papers). Use when the user wants to (re)build the hands-off daily pipeline, check whether it is still running, edit what it does each day, or run a test now. Trigger on: "定时任务 / scheduled routine / citation outreach / 求引用 / niw draft pipeline". Manages the routine via the RemoteTrigger (claude.ai code triggers) API; does NOT send email (draft-only).
---

# NIW citation-outreach scheduler

This skill owns the **daily cloud routine** that autonomously creates Gmail *drafts* asking authors of relevant recent papers to cite Jasper's work. It is the hands-off, self-sustaining version. The user reviews the drafts and sends them himself.

The routine already exists and runs daily at **14:00 UTC** (cron `0 14 * * *`). This skill lets you set it up from scratch, enforce the canonical config, verify health, edit the daily instructions, or fire a test run, all through the `RemoteTrigger` tool. Load it first: `ToolSearch query "select:RemoteTrigger"`.

## Files in this skill (single source of truth)
- `routine-config.json` — the full RemoteTrigger `body` scaffold, with `content` set to the placeholder `__DAILY_PROMPT__`. Also holds `known_trigger_id`.
- `daily-prompt.md` — the 7-step instructions the cloud agent executes each run. **Edit this to change what the routine does.** It is the exact prompt currently live.

To build the RemoteTrigger `body`: read `routine-config.json`, read `daily-prompt.md`, and replace the string `__DAILY_PROMPT__` inside the body with the full text of `daily-prompt.md`. That combined object is what you pass as `body`.

## Non-negotiable guardrails
1. **Draft-only, never send.** The routine and this skill only ever CREATE Gmail drafts. Do not change `daily-prompt.md` or the config toward auto-sending unless the user explicitly asks for it in this conversation. This is a deliberate safety gate (misattributed authors / off-topic papers must never auto-send under the user's name).
2. **Gmail is the only cross-run state.** No git push, no disk persistence. Don't add steps that assume written files survive between runs.
3. **Email lookup goes through Monid**, never in-sandbox scraping. That is the fix that ended the empty-run era; don't undo it.
4. Keep the two MCP connectors (Gmail + Monid) and `model: claude-sonnet-5`. If a run fails with an MCP/tool error, first check these are still attached before rewriting anything.

## Operations

### A. Verify / health-check (default when the user asks "is it still working?")
1. `RemoteTrigger action=get trigger_id=<known_trigger_id>`.
2. Report, in Chinese: `enabled`, `cron_expression`, `last_fired_at`, `next_run_at`, `model`, and that both Gmail + Monid connectors are present. Green if `last_fired_at` is within the last ~24h of a scheduled slot and `enabled=true`.
3. Note that "0 drafts on a given day" is a normal supply ceiling, not a failure (the backlog of un-contacted relevant authors is finite; 35+ already contacted). Only treat it as broken if runs error out or the connectors/model drifted.

### B. Set up / repair (enforce canonical config)
Use when the routine is missing, was edited by hand, drifted, or the user wants to rebuild it.
1. Build the `body` (config scaffold + substituted daily prompt) as described above.
2. If `known_trigger_id` still resolves via `get`: `RemoteTrigger action=update trigger_id=<id> body=<body>`.
   If it is gone (routines can't be deleted via API, only disabled, so this is rare): `RemoteTrigger action=create body=<body>`, then record the new `id` back into `routine-config.json`'s `known_trigger_id` and into the memory file.
3. Relay the server-parsed next run time and the claude.ai routine URL the tool returns. Confirm the time reads as 14:00 UTC.

### C. Edit what it does each day
1. Edit `daily-prompt.md` (that is the source of truth for the run instructions).
2. Then run **Operation B** to push the change into the live routine. An edit to the file alone does nothing until you update the trigger.

### D. Run a test now (manual fire)
1. Warn the user it will spend real money on Monid (roughly $0.2–0.5 per run for Exa email lookups) and may create new drafts.
2. `RemoteTrigger action=run trigger_id=<known_trigger_id>`.
3. When it finishes, results appear in the routine's claude.ai session and as new Gmail drafts; summarize the Step-7 output if available.

## Reference facts
- trigger_id: `trig_01NVJBfj5VDDux9HgjisQr9n` · repo: `github.com/Jasper0122/begging-for-niw-eb1a-citation`
- environment_id: `env_01H5ixMp5SAq3dMfLhVG53e9`
- Gmail connector `bf2a3d5f-bbd5-4466-9dd1-d1822f0edb4e` · Monid connector `51371c3e-5e3f-4fc8-a2de-5eb30f0ddb81`
- Verified end-to-end 2026-07-12 (created real drafts, user sent them). Last confirmed fire 2026-07-14 14:07 UTC.
- Related memory: `project_niw_outreach_routine.md`. The interactive/manual counterpart lives in the repo at `.claude/commands/niw-citation.md` (that one is for hands-on sessions; THIS skill is the automated scheduler).
