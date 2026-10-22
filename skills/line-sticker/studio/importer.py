"""Move downloaded images from inbox/ into source/NN.png (art/NN.png with code lettering)."""
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from .images import is_background_transparent, remove_background
from .theme import ThemeError

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass
class ImportResult:
    imported: list = field(default_factory=list)   # (original name, n)
    leftover: list = field(default_factory=list)   # names with no free slot
    warnings: list = field(default_factory=list)


def inbox_files(theme):
    if not theme.inbox_dir.exists():
        return []
    files = [p for p in theme.inbox_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    return sorted(files, key=lambda p: (p.stat().st_mtime, p.name))


def _archive(src, folder, prefix=""):
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{prefix}{src.name}"
    if dest.exists():
        dest = folder / f"{prefix}{src.stem}-{time.strftime('%Y%m%d-%H%M%S')}{src.suffix}"
    shutil.move(str(src), str(dest))


def import_images(theme, as_number=None, files=None, keep_bg=False):
    """Assign images to sticker numbers.

    Files named like 05.png or 05-wave.png go to that number (replacing what is there).
    Every other image in inbox/ (oldest first) fills the lowest missing numbers.
    as_number: put exactly one file at that number, replacing any existing image
    (the old one is kept in inbox/_replaced/).
    A white/checkered background is cut away automatically unless keep_bg is set.
    Originals that came from inbox/ are moved to inbox/_imported/.
    """
    files = [Path(f) for f in files] if files else inbox_files(theme)
    result = ImportResult()
    if not files:
        return result

    if as_number is not None:
        if len(files) != 1:
            raise ThemeError("--as needs exactly one file")
        if not 1 <= as_number <= theme.count:
            raise ThemeError(f"--as {as_number} is outside 1..{theme.count}")
        pairs = [(files[0], as_number)]
    else:
        pairs, unnumbered = [], []
        for f in files:
            m = re.match(r"(\d{1,2})(?:[-_ ].*)?$", f.stem)
            n = int(m.group(1)) if m else 0
            if 1 <= n <= theme.count:
                pairs.append((f, n))
            else:
                unnumbered.append(f)
        taken = {n for _, n in pairs}
        free = [n for n in theme.missing() if n not in taken]
        pairs += list(zip(unnumbered, free))
        result.leftover = [p.name for p in unnumbered[len(free):]]

    theme.raw_path(1).parent.mkdir(parents=True, exist_ok=True)
    for src, n in pairs:
        dest = theme.raw_path(n)
        if dest.exists():
            _archive(dest, theme.inbox_dir / "_replaced", prefix=f"{n:02d}-")
        with Image.open(src) as im:
            im = im.convert("RGBA")
            if not is_background_transparent(im):
                label = f"{n:02d}.png ({src.name})"
                if keep_bg:
                    result.warnings.append(f"{label}: พื้นหลังไม่ใส (--keep-bg จึงไม่ได้ลบ)")
                else:
                    im, why = remove_background(im)
                    result.warnings.append(
                        f"{label}: {why} ควรสั่ง ChatGPT ทำพื้นใสใหม่" if why
                        else f"{label}: ลบพื้นหลังขาว/ลายตารางให้อัตโนมัติแล้ว ตรวจดูใน preview หลัง build")
            im.save(dest, "PNG")
        if src.parent.resolve() == theme.inbox_dir.resolve():
            _archive(src, theme.inbox_dir / "_imported")
        result.imported.append((src.name, n))
    return result
