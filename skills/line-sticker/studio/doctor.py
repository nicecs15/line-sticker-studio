"""python sticker.py doctor: check that this machine can make stickers end to end."""
import importlib
import shutil
import subprocess
import sys

from .theme import ROOT, THEMES_DIR

REQUIREMENTS = ROOT / "requirements.txt"

PACKAGES = (("PIL", "pillow"), ("yaml", "pyyaml"), ("numpy", "numpy"), ("uharfbuzz", "uharfbuzz"))


def _codex_login(exe):
    try:
        proc = subprocess.run([exe, "login", "status"], capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    text = ((proc.stdout or b"") + (proc.stderr or b"")).decode("utf-8", "replace").strip()
    return proc.returncode == 0, text.splitlines()[0] if text else ""


def doctor(log=print):
    """Print one line per check; return True when everything needed is in place."""
    ok = True

    def line(passed, label, fix=""):
        nonlocal ok
        ok = ok and passed
        log(f"  {'OK ' if passed else 'XX '} {label}" + ("" if passed or not fix else f"\n       -> {fix}"))

    line(sys.version_info >= (3, 9), f"Python {sys.version.split()[0]}", "install Python 3.9 or newer")
    for module, pip_name in PACKAGES:
        try:
            importlib.import_module(module)
            line(True, f"package {pip_name}")
        except ImportError:
            line(False, f"package {pip_name}", f"python -m pip install -r \"{REQUIREMENTS}\"")

    from .lettering import FONTS_DIR
    fonts = sorted(p.stem for p in FONTS_DIR.glob("*.[ot]tf"))
    line(bool(fonts), f"fonts: {', '.join(fonts) or 'none'}", f"put a Thai .ttf in {FONTS_DIR}")

    exe = shutil.which("codex")
    if not exe:
        log("  --  Codex CLI not found (needed only for `generate`)\n"
            "       -> npm i -g @openai/codex  then  codex login  (sign in with ChatGPT)\n"
            "       -> or make images in ChatGPT yourself and use `import`")
    else:
        # Advisory only: inside a Codex sandbox the login is unreadable and reports "Not logged in".
        logged_in, status = _codex_login(exe)
        if logged_in and "not logged in" not in status.lower():
            line(True, f"Codex CLI: {status}")
        else:
            log(f"  --  Codex CLI: {status or 'login status unknown'} (needed only for `generate`)\n"
                "       -> if this runs inside a Codex sandbox, ignore it: the sandbox cannot see the login\n"
                "       -> otherwise run: codex login  (sign in with your ChatGPT account)")

    log(f"  --  sticker sets folder: {THEMES_DIR}")
    log("Ready to make stickers." if ok else "Fix the XX lines above, then run doctor again.")
    return ok
