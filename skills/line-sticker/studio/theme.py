"""Load and validate a theme folder: themes/<id>/theme.yaml + art/, source/, inbox/, dist/."""
import os
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent   # the skill folder: code, fonts, styles
# Sticker sets live with the user's work, not inside the installed skill.
THEMES_DIR = Path(os.environ.get("LINE_STICKER_THEMES") or Path.cwd() / "themes").resolve()
STYLE_DIR = ROOT / "style"
# How to run the CLI from the current folder, for hints printed to people.
CLI = "python sticker.py" if Path.cwd().resolve() == ROOT else f'python "{ROOT / "sticker.py"}"'
VALID_COUNTS = (8, 16, 24, 32, 40)
LINE_LANGS = ("en", "th")   # LINE Creators Market requires en; th is shown to Thai users
TEXT_POSITIONS = ("top", "bottom")
DEFAULT_FONT = "Kanit-ExtraBold"
DEFAULT_COLORS = ("#FF5A5F", "#2E86DE", "#20A35A", "#F39C12", "#9B59B6", "#E8590C", "#0FA5A0", "#D6336C")
DEFAULT_OUTLINE = "#2B2B35"


class ThemeError(Exception):
    pass


@dataclass
class Sticker:
    n: int
    text: str
    pose: str = ""
    props: str = ""
    text_style: str = ""
    color: str = ""          # lettering colour for this sticker (code lettering only)

    @property
    def label(self):
        """Caption on one line for logs and tables: line breaks shown as ' / '."""
        return " / ".join(ln.strip() for ln in self.text.splitlines() if ln.strip())


@dataclass
class Lettering:
    """Captions typed by the program with a real font, on top of text-free AI art."""
    font: str = DEFAULT_FONT
    colors: tuple = DEFAULT_COLORS
    outline: str = DEFAULT_OUTLINE
    position: str = "top"


@dataclass
class Listing:
    """Sale-page text for LINE Creators Market: {lang: (title, description)} + copyright."""
    copyright: str = ""
    texts: dict = None


@dataclass
class Theme:
    id: str
    dir: Path
    name: str
    count: int
    character: str
    style_lock: str
    stickers: list
    main: int = 1
    tab_crop: tuple = None
    style_notes: str = ""
    line: Listing = None
    export_type: str = "regular"
    lettering: Lettering = None   # None: the image model draws the caption itself

    @property
    def art_dir(self):
        return self.dir / "art"

    @property
    def source_dir(self):
        return self.dir / "source"

    @property
    def inbox_dir(self):
        return self.dir / "inbox"

    @property
    def dist_dir(self):
        return self.dir / "dist"

    @property
    def reference(self):
        return self.dir / "reference.png"

    def source_path(self, n):
        return self.source_dir / f"{n:02d}.png"

    def art_path(self, n):
        return self.art_dir / f"{n:02d}.png"

    def raw_path(self, n):
        """Where a generated/imported image goes: text-free art/ with code lettering, else source/."""
        return self.art_path(n) if self.lettering else self.source_path(n)

    def done(self):
        return [n for n in range(1, self.count + 1) if self.raw_path(n).exists()]

    def missing(self):
        return [n for n in range(1, self.count + 1) if not self.raw_path(n).exists()]

    def undrafted(self):
        drafted = {s.n for s in self.stickers}
        return [n for n in range(1, self.count + 1) if n not in drafted]

    def sticker(self, n):
        return next((s for s in self.stickers if s.n == n), None)


def theme_dirs(themes_dir=THEMES_DIR):
    if not themes_dir.exists():
        return []
    return sorted(p for p in themes_dir.iterdir()
                  if (p / "theme.yaml").exists() and not p.name.startswith("_"))


def resolve(theme_id, themes_dir=THEMES_DIR):
    path = themes_dir / theme_id
    if not (path / "theme.yaml").exists():
        known = ", ".join(p.name for p in theme_dirs(themes_dir)) or "(none)"
        raise ThemeError(f"Theme '{theme_id}' not found. Known themes: {known}")
    return path


def load_theme(theme_dir, style_dir=STYLE_DIR):
    theme_dir = Path(theme_dir)
    where = f"{theme_dir.name}/theme.yaml"
    try:
        data = yaml.safe_load((theme_dir / "theme.yaml").read_text(encoding="utf-8-sig")) or {}
    except yaml.YAMLError as e:
        raise ThemeError(f"{where}: invalid YAML (ข้อความที่มี : หรือ \" ให้ครอบด้วยเครื่องหมายคำพูด)\n{e}")

    for key in ("name", "count", "character"):
        if not data.get(key):
            raise ThemeError(f"{where}: missing '{key}'")
    count = int(data["count"])
    if count not in VALID_COUNTS:
        raise ThemeError(f"{where}: count must be one of {VALID_COUNTS}, got {count}")

    style_name = data.get("style", "default")
    style_file = style_dir / f"{style_name}.yaml"
    if not style_file.exists():
        raise ThemeError(f"{where}: style '{style_name}' not found ({style_file})")
    style_lock = (yaml.safe_load(style_file.read_text(encoding="utf-8-sig")) or {}).get("lock", "")

    stickers, seen = [], set()
    for raw in data.get("stickers") or []:
        n = int(raw["n"])
        if n in seen:
            raise ThemeError(f"{where}: sticker {n} defined twice")
        if not 1 <= n <= count:
            raise ThemeError(f"{where}: sticker {n} is outside 1..{count}")
        seen.add(n)
        stickers.append(Sticker(
            n=n,
            # A literal "\n" (single-quoted or unquoted YAML) is still a line break.
            text=str(raw.get("text", "")).replace("\\n", "\n"),
            pose=str(raw.get("pose", "")).strip(),
            props=str(raw.get("props", "")).strip(),
            text_style=str(raw.get("text_style", "")).strip(),
            color=_color(raw.get("color", ""), f"{where}: sticker {n} color"),
        ))
    stickers.sort(key=lambda s: s.n)
    from .duplicates import repeated_texts, repeated_poses
    duplicates = repeated_texts(stickers) + repeated_poses(stickers)
    if duplicates:
        raise ThemeError(f"{where}: " + "; ".join(duplicates))

    export_type = data.get("export_type", "regular")
    if export_type not in ("regular", "big"):
        raise ThemeError(f"{where}: export_type must be regular or big")

    main = int(data.get("main", 1))
    if not 1 <= main <= count:
        raise ThemeError(f"{where}: main {main} is outside 1..{count}")
    tab_crop = data.get("tab_crop")
    if tab_crop is not None:
        if len(tab_crop) != 4:
            raise ThemeError(f"{where}: tab_crop must be [left, top, right, bottom]")
        tab_crop = tuple(int(v) for v in tab_crop)

    lettering = _lettering(data.get("lettering"), where)

    line = data.get("line")
    if line is not None:
        if not isinstance(line, dict):
            raise ThemeError(f"{where}: 'line' must be a mapping (copyright, en, th)")
        texts = {}
        for lang in LINE_LANGS:
            entry = line.get(lang)
            if entry is None:
                continue
            if not isinstance(entry, dict):
                raise ThemeError(f"{where}: line.{lang} must have title and description")
            texts[lang] = (str(entry.get("title", "")).strip(), str(entry.get("description", "")).strip())
        line = Listing(copyright=str(line.get("copyright", "")).strip(), texts=texts)

    return Theme(
        id=theme_dir.name,
        dir=theme_dir,
        name=data["name"],
        count=count,
        character=str(data["character"]).strip(),
        style_lock=str(style_lock).strip(),
        stickers=stickers,
        main=main,
        tab_crop=tab_crop,
        style_notes=str(data.get("style_notes", "")).strip(),
        line=line,
        export_type=export_type,
        lettering=lettering,
    )


def _color(value, label):
    value = str(value or "").strip()
    if value:
        from PIL import ImageColor
        try:
            ImageColor.getrgb(value)
        except ValueError:
            raise ThemeError(f"{label}: '{value}' is not a colour (use e.g. \"#FF5A5F\")")
    return value


def _lettering(raw, where):
    """lettering: true | {font, colors, outline, position}; absent/false = AI draws the text."""
    if raw is None or raw is False:
        return None
    if raw is True:
        raw = {}
    if not isinstance(raw, dict):
        raise ThemeError(f"{where}: lettering must be true or a mapping (font, colors, outline, position)")
    position = str(raw.get("position", "top"))
    if position not in TEXT_POSITIONS:
        raise ThemeError(f"{where}: lettering.position must be one of {TEXT_POSITIONS}")
    colors = raw.get("colors") or DEFAULT_COLORS
    if isinstance(colors, str):
        colors = [colors]
    font = str(raw.get("font", DEFAULT_FONT))
    from .lettering import font_path
    font_path(font)
    return Lettering(
        font=font,
        colors=tuple(_color(c, f"{where}: lettering.colors") for c in colors),
        outline=_color(raw.get("outline", DEFAULT_OUTLINE), f"{where}: lettering.outline"),
        position=position,
    )
