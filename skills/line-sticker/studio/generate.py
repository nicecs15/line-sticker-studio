"""Generate source/NN.png (art/NN.png with code lettering) automatically, through one of two backends:

- codex  (default): the local Codex CLI and its built-in image tool, billed to the ChatGPT plan
                    Codex is logged in with; no API key needed.
- openai          : the OpenAI Images API (gpt-image-1); needs `pip install openai` and
                    OPENAI_API_KEY, and costs money per image.
"""
import base64
import io
import os
import shutil
import subprocess
import time

from PIL import Image

from .images import is_background_transparent, remove_background
from .prompts import sticker_prompt
from .theme import ThemeError

BACKENDS = ("codex", "openai")
DEFAULT_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
SIZE = "1024x1024"
BIG_SIZE = "1024x1536"   # Big Stickers are portrait

CODEX_TIMEOUT = 15 * 60
CODEX_ATTEMPTS = 3
CODEX_RETRY_WAIT = 30
CODEX_BUSY_MARKERS = ("at capacity", "rate limit", "too many requests", "temporarily unavailable")


def parse_range(spec, count):
    """'11-20,25' -> [11..20, 25]."""
    nums = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        lo, _, hi = part.partition("-")
        lo, hi = int(lo), int(hi or lo)
        if lo > hi or lo < 1 or hi > count:
            raise ThemeError(f"bad range '{part}' (stickers are 1..{count})")
        nums.update(range(lo, hi + 1))
    return sorted(nums)


# ---------- OpenAI API backend ----------

def make_client():
    if not os.environ.get("OPENAI_API_KEY"):
        raise ThemeError("OPENAI_API_KEY is not set")
    try:
        from openai import OpenAI
    except ImportError:
        raise ThemeError("openai package missing: pip install openai")
    return OpenAI()


def _api_size(theme):
    return BIG_SIZE if theme.export_type == "big" else SIZE


def _openai_request(client, theme, sticker, model, quality):
    if theme.reference.exists():
        with open(theme.reference, "rb") as ref:
            resp = client.images.edit(model=model, image=ref,
                                      prompt=sticker_prompt(theme, sticker, True),
                                      size=_api_size(theme), background="transparent", quality=quality)
    else:
        resp = client.images.generate(model=model,
                                      prompt=sticker_prompt(theme, sticker, False),
                                      size=_api_size(theme), background="transparent", quality=quality)
    data = base64.b64decode(resp.data[0].b64_json)
    return Image.open(io.BytesIO(data)).convert("RGBA")


# ---------- Codex CLI backend ----------

def codex_executable():
    exe = shutil.which("codex")
    if not exe:
        raise ThemeError("Codex CLI not found on PATH (npm i -g @openai/codex, then `codex login`)")
    return exe


def _size_line(theme):
    if theme.export_type == "big":
        return "Use a portrait image size (1024x1536), not square or landscape."
    return "Use a square image size (1024x1024), not portrait or landscape."


def _codex_task(theme, sticker, out_name):
    has_ref = theme.reference.exists()
    ref_line = ("Use the attached reference.png as the character reference.\n" if has_ref else "")
    return (f"Generate ONE image with your built-in image generation tool. {ref_line}"
            f"Ask for a transparent background and keep the generated alpha.\n"
            f"{_size_line(theme)}\n"
            f"Save the generated image as a PNG file named {out_name} in the current working directory.\n"
            f"Do not modify any other files. When done, reply with the absolute path of the saved file.\n\n"
            f"Image prompt:\n{sticker_prompt(theme, sticker, has_ref)}\n")


def _codex_request(theme, sticker, run=subprocess.run, wait=time.sleep, log=print):
    """Run one `codex exec` in inbox/_codex/NN/ and return the image it saved there."""
    work = theme.inbox_dir / "_codex" / f"{sticker.n:02d}"
    work.mkdir(parents=True, exist_ok=True)
    out_name = f"{sticker.n:02d}.png"
    out = work / out_name
    task = _codex_task(theme, sticker, out_name)
    (work / "task.txt").write_text(task, encoding="utf-8")

    cmd = [codex_executable(), "exec", "--skip-git-repo-check", "--ephemeral",
           "-s", "workspace-write", "-C", str(work), "-o", str(work / "last.txt")]
    if theme.reference.exists():
        shutil.copyfile(theme.reference, work / "reference.png")
        cmd += ["-i", str(work / "reference.png")]
    cmd.append("-")

    last_error = ""
    for attempt in range(1, CODEX_ATTEMPTS + 1):
        if out.exists():
            out.unlink()
        try:
            proc = run(cmd, input=task.encode("utf-8"), capture_output=True, timeout=CODEX_TIMEOUT)
            output = (proc.stdout or b"").decode("utf-8", "replace") + (proc.stderr or b"").decode("utf-8", "replace")
        except subprocess.TimeoutExpired:
            output = f"timed out after {CODEX_TIMEOUT // 60} min"
        (work / "run.log").write_text(output, encoding="utf-8")
        if out.exists():
            with Image.open(out) as im:
                return im.convert("RGBA")
        lines = [ln for ln in output.splitlines() if ln.strip()]
        last_error = lines[-1] if lines else "codex produced no image"
        busy = any(m in output.lower() for m in CODEX_BUSY_MARKERS)
        if attempt < CODEX_ATTEMPTS and busy:
            log(f"    codex busy ({last_error}); retry {attempt + 1}/{CODEX_ATTEMPTS} in {CODEX_RETRY_WAIT}s")
            wait(CODEX_RETRY_WAIT)
            continue
        break
    raise RuntimeError(f"{last_error} (log: {work / 'run.log'})")


# ---------- shared driver ----------

def generate(theme, numbers=None, via="codex", client=None, model=DEFAULT_MODEL, quality="high",
             force=False, dry_run=False, log=print, run=subprocess.run, wait=time.sleep):
    """Generate the given (or all missing) stickers. Returns (generated, failed) number lists.

    With no reference.png, the first generated image becomes reference.png so the
    rest of the set is drawn from it. White/checkered backgrounds are removed like `import` does.
    """
    if via not in BACKENDS:
        raise ThemeError(f"--via must be one of {BACKENDS}")
    targets = numbers or theme.missing()
    if not force:
        targets = [n for n in targets if not theme.raw_path(n).exists()]
    undrafted = [n for n in targets if theme.sticker(n) is None]
    if undrafted:
        log(f"skip (no text drafted in theme.yaml): {undrafted}")
    targets = [n for n in targets if theme.sticker(n) is not None]
    if not targets:
        log("nothing to generate")
        return [], []

    engine = "Codex CLI" if via == "codex" else f"{model} ({quality})"
    if dry_run:
        for n in targets:
            log(f"--- {n:02d} ---\n{sticker_prompt(theme, theme.sticker(n), theme.reference.exists())}\n")
        log(f"{len(targets)} image(s) would be generated with {engine}")
        return [], []

    if via == "codex":
        codex_executable()
    else:
        client = client or make_client()
    theme.raw_path(1).parent.mkdir(parents=True, exist_ok=True)
    log(f"Generating {len(targets)} image(s) with {engine}")
    generated, failed = [], []
    for i, n in enumerate(targets, 1):
        sticker = theme.sticker(n)
        log(f"  [{i}/{len(targets)}] {n:02d} {sticker.label} ...")
        started = time.time()
        try:
            if via == "codex":
                im = _codex_request(theme, sticker, run=run, wait=wait, log=log)
            else:
                im = _openai_request(client, theme, sticker, model, quality)
        except Exception as e:  # keep going; one bad image should not stop the batch
            log(f"  {n:02d} failed: {e}")
            failed.append(n)
            continue
        if not is_background_transparent(im):
            im, why = remove_background(im)
            log(f"  {n:02d} background: {why or 'removed white/checkered background'}")
        im.save(theme.raw_path(n), "PNG")
        generated.append(n)
        log(f"  {n:02d} done in {time.time() - started:.0f}s")
        if not theme.reference.exists():
            shutil.copyfile(theme.raw_path(n), theme.reference)
            log(f"  reference.png <- {n:02d}.png (ตรวจดูก่อนว่าชอบตัวละครนี้ ถ้าไม่ชอบให้ลบแล้วรันใหม่)")
    return generated, failed
