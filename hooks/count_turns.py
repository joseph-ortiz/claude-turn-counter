#!/usr/bin/env python3
"""Count user prompts (turns) in a Claude Code transcript JSONL.

Usage: count_turns.py <transcript_path>
Prints an integer. A "turn" = a real user prompt, NOT a tool_result echo
(tool results also arrive as type=="user" but carry a tool_result content block).
Never raises: prints 0 on any error so the statusline never breaks.
"""
import json
import sys


def count(path):
    n = 0
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") != "user":
                continue
            msg = e.get("message") or {}
            c = msg.get("content")
            if isinstance(c, str):
                n += 1
                continue
            if isinstance(c, list):
                # tool_result echoes are not user turns
                if any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c):
                    continue
                n += 1
    return n


def main():
    if len(sys.argv) < 2:
        print(0)
        return
    try:
        print(count(sys.argv[1]))
    except Exception:
        print(0)


if __name__ == "__main__":
    main()
