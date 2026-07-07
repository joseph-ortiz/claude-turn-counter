#!/usr/bin/env python3
"""Claude Code Stop hook: soft, one-time context reminder.

When a session reaches WARN_LIMIT (default 15) user turns, fire ONCE a
non-blocking `systemMessage` suggesting /compact or a fresh session. It never
uses {"decision":"block"}, so it will not interrupt you mid-thought.

Guards:
  - per-session marker file (.turn-reminder-<session_id>) -> fires once
  - stop_hook_active -> never re-fire inside a continuation

Env: WARN_LIMIT (default 15).
Reads the Stop-hook JSON from stdin; prints the reminder JSON to stdout (or nothing).
Never raises.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLAUDE_DIR = os.path.dirname(HERE)


def env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def count_turns(transcript_path):
    try:
        sys.path.insert(0, HERE)
        import count_turns as ct
        return ct.count(transcript_path)
    except Exception:
        return 0


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except Exception:
        return

    if data.get("stop_hook_active"):
        return

    transcript = data.get("transcript_path") or ""
    if not transcript or not os.path.isfile(transcript):
        return

    warn = env_int("WARN_LIMIT", 15)
    n = count_turns(transcript)
    if n < warn:
        return

    session = re.sub(r"[^A-Za-z0-9_-]", "", str(data.get("session_id") or "nosession"))
    marker = os.path.join(CLAUDE_DIR, ".turn-reminder-" + (session or "nosession"))
    if os.path.exists(marker):
        return
    try:
        open(marker, "w").close()
    except Exception:
        pass  # if we can't write the marker, still send the reminder once this run

    msg = (
        "⚠️  %d turns reached — context is getting long. When you're ready "
        "(finish your current thought first), run /compact to condense the conversation, "
        "or start a fresh session to reset context." % n
    )
    sys.stdout.write(json.dumps({"systemMessage": msg}))


if __name__ == "__main__":
    main()
