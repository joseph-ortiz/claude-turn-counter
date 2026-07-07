#!/usr/bin/env python3
"""Claude Code statusLine: renders  ●  Turn N/LIMIT  with color escalation.

statusLine only allows ONE command, so this wraps any pre-existing statusLine:
install.py saves the original command into `.turn-counter-wrapped.txt` (next to
the .claude dir). If present, we run it first with the same stdin and print its
output, then append our turn segment. If absent, we print only the segment.

Env:
  WARN_LIMIT  (default 15)     -> yellow threshold + reminder turn
  TURN_LIMIT  (default 20)     -> red "WRAP UP" threshold
  TURN_DOCK   (default right)  -> "right" pads so the turn segment sits flush at the
                                  terminal's right edge; "left" appends after the
                                  wrapped output (the old behavior). Right-docking needs
                                  a known terminal width (COLUMNS or a tty); when width
                                  is unknown it falls back to left automatically.
Never raises: on any error it prints just the segment (or nothing) so the bar survives.
"""
import json
import os
import re
import shutil
import subprocess
import sys

ANSI_RE = re.compile(r"\033\[[0-9;]*m")

HERE = os.path.dirname(os.path.abspath(__file__))
CLAUDE_DIR = os.path.dirname(HERE)  # hooks/ lives inside the .claude dir
WRAPPED = os.path.join(CLAUDE_DIR, ".turn-counter-wrapped.txt")

GREEN = "\033[38;5;71m"
YELLOW = "\033[38;5;178m"
RED = "\033[1;38;5;196m"
RESET = "\033[0m"


def env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def visible_len(s):
    """Character width ignoring ANSI color escapes."""
    return len(ANSI_RE.sub("", s))


def term_width():
    """Best-effort terminal width; 0 when genuinely unknown (so we skip docking)."""
    cols = env_int("COLUMNS", 0)
    if cols > 0:
        return cols
    try:
        cols = shutil.get_terminal_size(fallback=(0, 0)).columns
    except Exception:
        cols = 0
    return cols if cols > 0 else 0


def count_turns(transcript_path):
    """Import the sibling counter; fall back to 0 on any problem."""
    try:
        sys.path.insert(0, HERE)
        import count_turns as ct
        return ct.count(transcript_path)
    except Exception:
        return 0


def render_wrapped(raw):
    """Run the pre-existing statusLine command with the same stdin; return its stdout."""
    try:
        with open(WRAPPED, "r", encoding="utf-8") as fh:
            cmd = fh.read().strip()
        if not cmd:
            return ""
        proc = subprocess.run(
            cmd, shell=True, input=raw,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5,
        )
        return proc.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def main():
    raw = sys.stdin.buffer.read()

    out = ""
    if os.path.isfile(WRAPPED):
        out = render_wrapped(raw)

    warn = env_int("WARN_LIMIT", 15)
    limit = env_int("TURN_LIMIT", 20)

    try:
        data = json.loads(raw.decode("utf-8", "replace"))
        transcript = data.get("transcript_path") or ""
    except Exception:
        transcript = ""

    segment = ""
    if transcript and os.path.isfile(transcript):
        n = count_turns(transcript)
        if n >= limit:
            segment = "%s●%s  Turn %d/%d — WRAP UP%s" % (RED, RESET + RED, n, limit, RESET)
        elif n >= warn:
            segment = "%s●%s  Turn %d/%d%s" % (YELLOW, RESET + YELLOW, n, limit, RESET)
        else:
            segment = "%s●%s  Turn %d/%d%s" % (GREEN, RESET + GREEN, n, limit, RESET)

    if out and segment:
        out = out.rstrip("\n")
        dock = os.environ.get("TURN_DOCK", "right").strip().lower()
        width = term_width() if dock != "left" else 0
        # Pad so the segment sits flush at the right edge; +2 keeps a min gap so it
        # never collides with the wrapped output. Fall back to a 2-space join when the
        # width is unknown or too narrow to dock without overlap.
        pad = width - visible_len(out) - visible_len(segment)
        if dock != "left" and width and pad >= 2:
            sys.stdout.write(out + (" " * pad) + segment)
        else:
            sys.stdout.write(out + "  " + segment)
    elif segment:
        sys.stdout.write(segment)
    elif out:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()
