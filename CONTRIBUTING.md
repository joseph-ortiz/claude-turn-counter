# Contributing

Thanks for your interest! This is a deliberately tiny tool — the bar for changes is
"does it stay small, dependency-free, and hard to break." Please read this before opening a PR.

## Philosophy

- **Standard library only.** No pip dependencies. The whole point is that it runs anywhere
  Python (which Claude Code already needs) runs. A PR that adds a dependency will be declined
  unless it removes far more complexity than it adds.
- **Hooks must never crash.** `count_turns.py`, `statusline_turns.py`, and `turn_reminder.py`
  run on every render / every stop. If one raises, it can break the status bar or a session.
  Every hook catches broadly and degrades to "print nothing / print 0" on error. Keep it that way.
- **Non-intrusive by default.** The reminder uses a Stop-hook `systemMessage` (a soft warning).
  It must never use `{"decision": "block"}` or otherwise interrupt the user mid-thought.
- **Small surface.** New config knobs should be env vars with sane defaults, documented in the
  README table.

## Two invariants to preserve

1. **`statusLine` is a single command slot.** To add a segment you wrap the existing command —
   never assume you own the whole bar. `statusline_turns.py` runs the wrapped command first,
   then appends. `install.py` saves the prior command into `.turn-counter-wrapped.txt`.
2. **`systemMessage` warns without interrupting.** That distinction (vs `decision: block`) is
   the core UX promise. Don't break it.

## Dev setup

No build step. Clone, edit, run the scripts directly.

```bash
git clone https://github.com/<you>/claude-turn-counter.git
cd claude-turn-counter
```

### Manual test

Make a fake transcript and exercise each hook:

```bash
# 15 real user turns + tool_result echoes that must NOT count
python3 - <<'PY'
import json
with open("/tmp/t.jsonl", "w") as f:
    for i in range(15):
        f.write(json.dumps({"type":"user","message":{"content":f"p{i}"}}) + "\n")
        f.write(json.dumps({"type":"user","message":{"content":[{"type":"tool_result","content":"x"}]}}) + "\n")
PY

python3 hooks/count_turns.py /tmp/t.jsonl              # -> 15  (echoes excluded)

printf '{"transcript_path":"/tmp/t.jsonl"}' \
  | python3 hooks/statusline_turns.py; echo           # -> yellow ●  Turn 15/20

printf '{"transcript_path":"/tmp/t.jsonl","session_id":"x","stop_hook_active":false}' \
  | python3 hooks/turn_reminder.py; echo              # -> systemMessage JSON
```

### Test the installer safely

Point it at a throwaway config dir so you never touch your real `~/.claude`:

```bash
mkdir -p /tmp/fakecfg
CLAUDE_CONFIG_DIR=/tmp/fakecfg python3 install.py
CLAUDE_CONFIG_DIR=/tmp/fakecfg python3 install.py            # re-run: must be idempotent
CLAUDE_CONFIG_DIR=/tmp/fakecfg python3 install.py --uninstall
```

Verify: an existing `statusLine` is preserved (wrapped), an existing `Stop` hook survives,
re-running doesn't duplicate anything, and `--uninstall` restores the original bar.

## Pull requests

- One focused change per PR. Describe the behavior before/after.
- If you touched a hook, paste the manual-test output above showing it still works on
  Windows *or* macOS/Linux (ideally note which you tested).
- Keep the README's config table and the invariants above in sync with any behavior change.
- Be kind in issues and reviews.

## Ideas welcome

Good small additions: opt-in per-project thresholds, a token-based (not turn-based) mode,
a PowerShell-free Windows sanity note, alternate color themes. Open an issue to discuss before
building anything larger than a hook tweak.
