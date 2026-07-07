#!/usr/bin/env python3
"""Installer for claude-turn-counter.

Wires a live turn counter into your Claude Code status bar plus a one-time,
non-blocking reminder at WARN_LIMIT turns. Cross-platform (Windows/macOS/Linux),
no bash. Run:

    python install.py            # install / update
    python install.py --uninstall

What it does:
  1. Finds your Claude config dir ($CLAUDE_CONFIG_DIR or ~/.claude).
  2. Copies the three hook scripts into <config>/hooks/.
  3. Backs up settings.json -> settings.json.bak-turncounter.
  4. If you already have a statusLine command, saves it so ours WRAPS it
     (your original bar is preserved, the counter is appended).
  5. Points statusLine at statusline_turns.py and ADDS a Stop hook for
     turn_reminder.py. Existing hooks are left untouched.
Idempotent: re-running will not double-wrap or duplicate the Stop hook.
"""
import json
import os
import shutil
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
HOOK_FILES = ["count_turns.py", "statusline_turns.py", "turn_reminder.py"]
WRAP_MARKER = "statusline_turns.py"
REMINDER_MARKER = "turn_reminder.py"


def config_dir():
    d = os.environ.get("CLAUDE_CONFIG_DIR")
    if d:
        return os.path.abspath(os.path.expanduser(d))
    return os.path.join(os.path.expanduser("~"), ".claude")


def quoted_cmd(script_path):
    """`"python" "script"` — quote both so spaces in paths are safe on Windows."""
    return '"%s" "%s"' % (sys.executable, script_path)


def load_settings(path):
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as e:
        print("ERROR: could not parse %s (%s). Fix or move it, then re-run." % (path, e))
        sys.exit(1)


def install(cfg):
    hooks_dir = os.path.join(cfg, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)

    # 1. copy hook scripts
    for f in HOOK_FILES:
        src = os.path.join(REPO, "hooks", f)
        dst = os.path.join(hooks_dir, f)
        shutil.copyfile(src, dst)
        try:
            os.chmod(dst, 0o755)
        except Exception:
            pass
    print("Copied hooks -> %s" % hooks_dir)

    settings_path = os.path.join(cfg, "settings.json")
    settings = load_settings(settings_path)

    # 2. backup
    if os.path.isfile(settings_path):
        shutil.copyfile(settings_path, settings_path + ".bak-turncounter")
        print("Backed up settings.json -> settings.json.bak-turncounter")

    statusline_script = os.path.join(hooks_dir, "statusline_turns.py")
    reminder_script = os.path.join(hooks_dir, "turn_reminder.py")
    wrap_file = os.path.join(cfg, ".turn-counter-wrapped.txt")

    # 3. statusLine — wrap any pre-existing command (once)
    existing = settings.get("statusLine")
    existing_cmd = existing.get("command") if isinstance(existing, dict) else None
    if existing_cmd and WRAP_MARKER not in existing_cmd:
        with open(wrap_file, "w", encoding="utf-8") as fh:
            fh.write(existing_cmd)
        print("Wrapped existing statusLine (preserved): %s" % existing_cmd)
    elif existing_cmd and WRAP_MARKER in existing_cmd:
        print("statusLine already ours — leaving wrap file as-is")

    settings["statusLine"] = {"type": "command", "command": quoted_cmd(statusline_script)}

    # 4. Stop hook — add ours if not already present
    hooks = settings.setdefault("hooks", {})
    stop = hooks.setdefault("Stop", [])
    already = any(
        REMINDER_MARKER in h.get("command", "")
        for entry in stop
        for h in entry.get("hooks", [])
    )
    if not already:
        stop.append({
            "hooks": [{
                "type": "command",
                "command": quoted_cmd(reminder_script),
                "timeout": 10,
            }]
        })
        print("Added Stop hook (turn_reminder.py)")
    else:
        print("Stop hook already present — skipped")

    # 5. write + verify
    with open(settings_path, "w", encoding="utf-8") as fh:
        json.dump(settings, fh, indent=2)
    with open(settings_path, "r", encoding="utf-8") as fh:
        json.load(fh)  # raises if we produced invalid JSON
    print("Wrote %s (valid JSON)" % settings_path)

    print("\nDone. Takes effect on your NEXT Claude Code session.")
    print("Tunables: env WARN_LIMIT (default 15), TURN_LIMIT (default 20).")


def uninstall(cfg):
    settings_path = os.path.join(cfg, "settings.json")
    settings = load_settings(settings_path)
    changed = False

    sl = settings.get("statusLine")
    if isinstance(sl, dict) and WRAP_MARKER in sl.get("command", ""):
        wrap_file = os.path.join(cfg, ".turn-counter-wrapped.txt")
        if os.path.isfile(wrap_file):
            with open(wrap_file, "r", encoding="utf-8") as fh:
                settings["statusLine"] = {"type": "command", "command": fh.read().strip()}
            os.remove(wrap_file)
            print("Restored original statusLine")
        else:
            settings.pop("statusLine", None)
            print("Removed statusLine (no original to restore)")
        changed = True

    stop = settings.get("hooks", {}).get("Stop", [])
    kept = [e for e in stop
            if not any(REMINDER_MARKER in h.get("command", "") for h in e.get("hooks", []))]
    if len(kept) != len(stop):
        settings["hooks"]["Stop"] = kept
        print("Removed Stop hook")
        changed = True

    if changed:
        with open(settings_path, "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2)
        print("Updated settings.json. Hook scripts left in hooks/ (delete manually if wanted).")
    else:
        print("Nothing to uninstall.")


def main():
    cfg = config_dir()
    if not os.path.isdir(cfg):
        print("Claude config dir not found: %s" % cfg)
        print("Set CLAUDE_CONFIG_DIR or install Claude Code first.")
        sys.exit(1)
    print("Claude config dir: %s" % cfg)
    if "--uninstall" in sys.argv:
        uninstall(cfg)
    else:
        install(cfg)


if __name__ == "__main__":
    main()
