# Vercept — AI Assistant Guidelines

## Project Overview

**Vercept** is a GUI-first AI agent for macOS that can:
- Capture and analyze screen state using OpenAI's vision models
- Plan and execute GUI actions (clicks, typing, scrolling)
- Maintain task memory and context across multiple steps
- Apply safety guardrails to prevent destructive actions

**Stack:**
- Python 3.x
- OpenAI API (GPT-4o for vision and planning)
- PyAutoGUI for GUI automation
- Tesseract OCR for text recognition
- Pillow for image processing
- Rich for terminal UI

**Key Files:**
- `main.py` — CLI entry point with signal handling
- `config.py` — Configuration management via .env
- `vercept/agent.py` — Main orchestration loop (perception → planning → execution → verification)
- `vercept/perception.py` — Screen capture and analysis
- `vercept/planner.py` — OpenAI-based task planning and action verification
- `vercept/executor.py` — GUI action execution (click, type, scroll, etc.)
- `vercept/memory.py` — Task context and action history tracking
- `vercept/safety.py` — Action validation and blocking (sudo prevention, etc.)
- `vercept/prompts.py` — System and user prompts for LLM calls

---

## Workflow Orchestration

### 1. Plan Mode Default

- **Enter plan mode for ANY non-trivial task** (3+ steps or architectural decisions)
- **If something goes sideways, STOP and re-plan immediately** — don't keep pushing
- **Use plan mode for verification steps**, not just building
- **Write detailed specs upfront** to reduce ambiguity
- For bug fixes on this codebase: analyze stack traces and OpenAI API responses before acting

### 2. Subagent Strategy

- **Use subagents liberally** to keep main context window clean
- **Offload research, exploration, and parallel analysis** to subagents
- For complex problems, throw more compute at it via subagents
- **One task per subagent** for focused execution
- For Vercept development: use Explore agents to map the agent loop flow or LLM prompt chains

### 3. Self-Improvement Loop

- **After ANY correction from the user: update tasks/lessons.md** with the pattern
- Write rules for yourself that prevent the same mistake
- **Ruthlessly iterate** on these lessons until mistake rate drops
- Review lessons at session start for relevant project
- For Vercept: capture patterns about common API failures, screen capture timing issues, safety edge cases

### 4. Verification Before Done

- **Never mark a task complete** without proving it works
- Diff behavior between main and your changes when relevant
- **Ask yourself: "Would a staff engineer approve this?"**
- **Run tests, check logs, demonstrate correctness**
- For Vercept: test with dry_run mode first; verify action execution doesn't break state

### 5. Demand Elegance (Balanced)

- **For non-trivial changes: pause and ask "is there a more elegant way?"**
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- **Skip this for simple, obvious fixes** — don't over-engineer
- **Challenge your own work** before presenting it
- For Vercept: consider whether safety checks belong in Executor, Safety, or Planner; refactor prompts to reduce token usage

### 6. Autonomous Bug Fixing

- **When given a bug report: just fix it. Don't ask for hand-holding**
- **Point at logs, errors, failing tests** — then resolve them
- **Zero context switching** required from the user
- Go fix failing CI tests without being told how
- For Vercept: if OpenAI rate limits hit, implement backoff; if perception fails, debug screenshot capture; if executor fails, check action params

---

## Task Management

### Plan First
- Write plan to `tasks/todo.md` with checkable items
- Break down multi-step changes (e.g., adding a new safety rule involves: safety.py logic → prompts.py guidance → agent.py flow → testing)

### Verify Plan
- Check in with the user before starting implementation
- For Vercept changes: flag if modification affects the agent's core loop or LLM prompts

### Track Progress
- Mark items complete as you go
- Don't batch up completions

### Explain Changes
- High-level summary at each step
- For Vercept: explain how changes affect perception → planning → execution loop

### Document Results
- Add review section to `tasks/todo.md`
- Link to commits or PR discussions

### Capture Lessons
- Update `tasks/lessons.md` after corrections
- For Vercept: "screen capture timing issues require +100ms delay in perception.py", etc.

---

## Core Principles

### Simplicity First
- **Make every change as simple as possible**
- **Impact minimal code**
- For Vercept: add new actions to executor.py, don't refactor the entire execution chain
- For safety changes: add a simple check in safety.py before adding complexity to the planner

### No Laziness
- **Find root causes. No temporary fixes. Senior developer standards.**
- If perception times out, fix the timeout logic; don't just increase the delay everywhere
- If prompt causes hallucinations, refine the prompt or add guard rails; don't skip verification

### Minimal Impact
- **Changes should only touch what's necessary**
- **Avoid introducing bugs**
- For Vercept: changes to executor.py should not affect planner.py; changes to memory.py should not require agent.py rewrites
- Prefer adding new methods over refactoring existing ones

---

## Development Workflows

### Adding a New GUI Action

1. **Define action** in a specific method in `executor.py` (e.g., `_execute_double_click`)
2. **Test execution** with dry_run mode first
3. **Add action type** to planner prompts if LLM should consider it
4. **Test end-to-end** with a simple task
5. **Document** in executor.py docstring

### Improving Safety Checks

1. **Identify risky action pattern** (e.g., "sudo rm -rf")
2. **Add check** to `safety.py` in appropriate method
3. **Consider false positives** — don't block legitimate uses (e.g., "sudo" in a help command)
4. **Add to `prompts.py`** guidance if planner should avoid triggering this
5. **Test with blocking and non-blocking examples**

### Fixing LLM Planning Issues

1. **Reproduce** with minimal example task
2. **Check `planner.py`** — verify system/user prompt and model parameters
3. **Review `prompts.py`** — are instructions clear? Are examples helpful?
4. **Check screen context** — is perception giving planner enough info?
5. **Refine prompts** (prefer prompt engineering over code changes)
6. **Test verification logic** — does planner correctly detect task completion?

### Debugging Screen Capture Issues

1. **Check `perception.py`** — is screenshot actually being captured?
2. **Check OCR** — tesseract output accuracy, language settings
3. **Check timing** — does action_delay need adjustment?
4. **Check scaling** — is screenshot_scale correct for screen resolution?
5. **Add logging** if needed, then revert before committing

### Handling OpenAI API Failures

1. **Identify error type** — rate limit, invalid API key, model unavailable, timeout
2. **For rate limits:** implement exponential backoff in `planner.py`
3. **For API key:** check config.py loading and .env setup
4. **For timeouts:** increase timeout in API calls, add retry logic
5. **Test with api_key validation** before running full agent loop

### Modifying Agent Loop

The core loop in `agent.py` is: Capture → Plan → Execute → Verify → Update Memory.

**Only modify if:**
- There's a genuine bug in the loop logic
- There's a performance bottleneck
- New step genuinely improves safety/reliability

**If changing:**
1. Write tests for the modified flow (even if informal)
2. Test with dry_run mode
3. Document why the change was necessary
4. Check for ripple effects on memory, safety, executor

---

## Configuration & Environment

**Required:**
- `OPENAI_API_KEY` — set in `.env` (see `.env.example`)

**Optional (in `.env`):**
- `VERCEPT_DRY_RUN=true` — log actions without executing

**Config values** (in `config.py` and `VerceptConfig`):
- `model` — default "gpt-4o" (do not change without testing vision capabilities)
- `screenshot_scale` — 0.5 by default (0.25 for high-res screens, 1.0 for low-res)
- `action_delay` — 0.5s default (increase if actions don't settle; decrease if too slow)
- `max_actions_per_task` — safety limit (50 by default)
- `max_retries` — per-action retry limit (3 by default)
- `confirmation_required` — block risky actions until user confirms
- `ocr_enabled` — enable OCR for on-screen text extraction

---

## Coding Conventions

### Module Responsibilities

| Module | Responsibility | Don't Handle |
|--------|---|---|
| `agent.py` | Orchestrate loop; display output; handle user interrupts | Action execution; LLM calls |
| `perception.py` | Capture screenshot; OCR text; describe screen state | Planning; action execution |
| `planner.py` | Generate next action via LLM; verify task success | Actually clicking; screen capture |
| `executor.py` | Execute actions (click, type, etc.); handle timing | Planning; verification |
| `memory.py` | Track actions, context, retries | Safety decisions; execution |
| `safety.py` | Block dangerous actions; validate action params | Execution; planning |
| `config.py` | Load configuration from environment | Runtime decision-making |

### Naming Conventions

- **Action types** (in planner output): lowercase with underscores (e.g., `click`, `type_text`, `double_click`, `scroll_down`)
- **Method names** in Executor: prefix with `_execute_` for action handlers (e.g., `_execute_click`)
- **Prompts** in prompts.py: clear purpose in function name (e.g., `get_planning_prompt`, `get_verification_prompt`)
- **Config variables**: snake_case (e.g., `max_actions_per_task`)

### Error Handling

- **LLM failures:** Log the error, add context to memory, ask user for clarification or retry
- **Action execution failures:** Log to memory, let planner decide whether to retry or adjust
- **Screen capture failures:** Raise exception, let agent loop catch and retry
- **Configuration errors:** Fail early in `load_config()` with clear error message

### Logging & Output

- Use `console.print()` from Rich for all user-facing output
- Use `[dim]` for debug info, `[yellow]` for warnings, `[red]` for errors, `[green]` for success
- Keep output concise — users should know task progress at a glance
- For debugging: add temporary logging, test, then remove before committing

### Type Hints & Docstrings

- Use type hints on public methods
- Docstrings only on complex methods or non-obvious parameters
- Don't add docstrings to simple getters or one-liners

---

## Git Workflow

### Branch Strategy

- **Main branch:** `master` — stable, tested code
- **Feature branches:** `claude/claude-md-{session-id}` — development branches for Claude Code
- Push to feature branch with: `git push -u origin <branch-name>`

### Commit Messages

- **Imperative mood:** "Add safety check for sudo" (not "Added…" or "Adds…")
- **Reference modules:** "executor.py: add double_click action" (not just "double click")
- **Reference functions/files:** "planner.py: improve screening logic" (not vague)
- **One logical change per commit**

### Pull Request Checklist

- [ ] Tested with dry_run mode
- [ ] No new dependencies added (or justified if added)
- [ ] No hardcoded values (use config.py)
- [ ] Safety checks verified (no unintended blocking)
- [ ] Prompts updated if LLM behavior changed
- [ ] Logging/output is clear (no debug prints left in)

---

## Common Pitfalls & How to Avoid

| Pitfall | Cause | Fix |
|---------|-------|-----|
| Actions execute too fast, state doesn't update | action_delay too low | Check `config.py`; increase by +0.2s |
| LLM keeps planning wrong actions | Prompt is ambiguous | Review `prompts.py`; add example or clarify instruction |
| Safety blocks legitimate actions | Overly broad regex/check | Refine `safety.py` check; test false positives |
| Perception fails on certain screens | Screenshot size/quality mismatch | Adjust `screenshot_scale` or OCR settings |
| Task never reaches "done" | Verification never returns task_complete | Debug `verify_success` logic in planner.py |
| Memory grows too large | Too many actions in task | Reduce max_actions_per_task or add early stopping |
| API rate limit hit | Too many quick requests | Add backoff in planner.py; batch requests |

---

## Testing & Validation

### Manual Testing

1. **Dry-run mode:** Set `VERCEPT_DRY_RUN=true`, run agent with simple task
2. **Verify output:** Check that actions are logged correctly without executing
3. **End-to-end test:** Run without dry-run on a controlled task (e.g., "open calculator")
4. **Safety test:** Attempt a blocked action; verify it's blocked with user prompt

### Code Review Checklist

Before marking tasks complete:
- [ ] Feature works as described
- [ ] No regression in existing features
- [ ] Safety not compromised
- [ ] Performance acceptable
- [ ] Code is readable and follows conventions
- [ ] Git history is clean

---

## When to Ask for Help

You should autonomously:
- Fix bugs you can identify from logs
- Improve prompts based on LLM behavior
- Add new safety checks
- Optimize performance
- Refactor within a module

You should ask the user:
- Before major architectural changes
- If you're unsure about intended behavior
- If safety trade-offs are involved
- If new dependencies are needed
- If task scope changes significantly

---

## Quick Reference

```
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Run
python main.py

# Dry-run (safe testing)
VERCEPT_DRY_RUN=true python main.py

# Debug perception
python -c "from vercept.perception import Perception; from config import load_config; p = Perception(load_config()); s = p.capture(); print(s)"
```

---

**Last Updated:** 2026-02-26
**Maintained by:** Claude Code AI Assistant
