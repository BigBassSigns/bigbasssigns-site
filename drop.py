#!/usr/bin/env python3
"""Mac droplet for sRGB Normalize.

Finder passes dropped files and folders as arguments. With no arguments,
the app asks for files or a folder. Results are shown in a dialog.
"""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys


def apple(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def run_osascript(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/usr/bin/osascript", "-"],
        input=source,
        text=True,
        capture_output=True,
    )


def alert(message: str) -> None:
    print(message)
    parts = message.split("\n")
    body = " & return & ".join(apple(part) for part in parts)
    run_osascript(
        "display dialog "
        + body
        + ' buttons {"OK"} default button "OK" with title "sRGB Normalize"'
    )


def notify(message: str) -> None:
    run_osascript(f"display notification {apple(message)} with title \"sRGB Normalize\"")


def choose_paths() -> list[str]:
    script = """
try
  set choice to button returned of (display dialog "Drop PNG or JPG files, or a folder of them, onto this app." buttons {"Cancel", "Choose Folder", "Choose Files"} default button "Choose Files" with title "sRGB Normalize")
on error
  return ""
end try
if choice is "Choose Folder" then
  try
    set picked to choose folder with prompt "Choose a folder of PNG or JPG files"
  on error
    return ""
  end try
  return POSIX path of picked
end if
try
  set picked to choose file with prompt "Choose PNG or JPG files" with multiple selections allowed of type {"public.png", "public.jpeg", "png", "jpg", "jpeg"}
on error
  return ""
end try
set out to ""
repeat with f in picked
  set out to out & POSIX path of f & linefeed
end repeat
return out
"""
    result = run_osascript(script)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def report(saved: list, errors: list[str], notes: list[str]) -> str:
    lines: list[str] = []
    if len(saved) == 1:
        lines.append(f"Saved {saved[0].name} next to the original.")
    elif saved:
        lines.append(f"Saved {len(saved)} files next to the originals.")
    if notes:
        lines.extend(notes[:8])
        if len(notes) > 8:
            lines.append(f"and {len(notes) - 8} more skipped")
    if errors:
        lines.append("Problems:")
        lines.extend(errors[:10])
        if len(errors) > 10:
            lines.append(f"and {len(errors) - 10} more")
    if not lines:
        lines.append("No PNG or JPG files found.")
    return "\n".join(lines)


def _main(argv: list[str]) -> int:
    import normalize

    incoming = [arg for arg in argv[1:] if not arg.startswith("-psn_")]
    if not incoming:
        incoming = choose_paths()
        if not incoming:
            return 0

    files, errors, notes = normalize.collect_inputs(incoming)
    if not files:
        alert(report([], errors, notes))
        return 1 if errors else 0

    count = len(files)
    noun = "image" if count == 1 else "images"
    notify(f"Converting {count} {noun}…")

    saved = []
    for path in files:
        captured = io.StringIO()
        try:
            with contextlib.redirect_stderr(captured):
                saved.append(normalize.normalize(path))
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        warning = captured.getvalue().strip()
        if warning:
            notes.append(f"{path.name}: {warning}")
        print(saved[-1])

    alert(report(saved, errors, notes))
    return 1 if errors else 0


def main(argv: list[str]) -> int:
    try:
        return _main(argv)
    except Exception as exc:
        alert(f"sRGB Normalize failed to start.\n{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
