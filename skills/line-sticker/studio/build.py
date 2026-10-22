"""Build a LINE Creators Market upload pack from source/NN.png."""
import re
import zipfile
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

from .images import MAX_BYTES, clean, fit, is_background_transparent, save_png
from .theme import LINE_LANGS, VALID_COUNTS, ThemeError

STICKER = (370, 320)   # LINE max W x H
BIG_STICKER = (396, 660)
BIG_MIN_ART_HEIGHT = 524
MARGIN = 10            # LINE asks for ~10px padding
MAIN = (240, 240)
TAB = (96, 74)
TITLE_MAX, DESCRIPTION_MAX, COPYRIGHT_MAX = 40, 160, 50   # LINE Creators Market field limits


@dataclass
class BuildResult:
    zip_path: object
    preview_path: object
    count: int
    notes: list = field(default_factory=list)


def _source_numbers(theme):
    if not theme.source_dir.exists():
        return []
    return sorted(int(p.stem) for p in theme.source_dir.glob("*.png") if re.fullmatch(r"\d{2}", p.stem))


def _preview(images, path, cols=8, cell=STICKER):
    rows = (len(images) + cols - 1) // cols
    label_h = 18
    sheet = Image.new("RGBA", (cols * cell[0], rows * (cell[1] + label_h)), (232, 236, 240, 255))
    draw = ImageDraw.Draw(sheet)
    for i, (n, im) in enumerate(images):
        x, y = (i % cols) * cell[0], (i // cols) * (cell[1] + label_h)
        draw.text((x + 6, y + 3), f"{n:02d}", fill=(60, 60, 60, 255))
        sheet.alpha_composite(im, (x, y + label_h))
    sheet.convert("RGB").save(path, "PNG", optimize=True)


def _listing(theme, path):
    """Write dist/line_info.txt (sale-page text to paste into Creators Market); return notes."""
    line = theme.line
    if line is None:
        return ["ยังไม่มีชื่อ/คำอธิบายสำหรับหน้าขาย LINE (เพิ่ม line: ใน theme.yaml)"]
    notes, out = [], [f"# {theme.name}: ข้อมูลหน้าขาย LINE Creators Market", ""]
    if "en" not in line.texts:
        notes.append("LINE ต้องมีชื่อ/คำอธิบายภาษาอังกฤษ (line.en)")
    for lang in LINE_LANGS:
        if lang not in line.texts:
            continue
        title, desc = line.texts[lang]
        for field_name, value, limit in (("title", title, TITLE_MAX), ("description", desc, DESCRIPTION_MAX)):
            if not value:
                notes.append(f"LINE {lang} {field_name} ว่างอยู่")
            elif len(value) > limit:
                notes.append(f"LINE {lang} {field_name} ยาว {len(value)}/{limit} ตัวอักษร")
        out += [f"[{lang}] Title ({len(title)}/{TITLE_MAX})", title, "",
                f"[{lang}] Description ({len(desc)}/{DESCRIPTION_MAX})", desc, ""]
    if not line.copyright:
        notes.append("LINE copyright ว่างอยู่")
    elif len(line.copyright) > COPYRIGHT_MAX:
        notes.append(f"LINE copyright ยาว {len(line.copyright)}/{COPYRIGHT_MAX} ตัวอักษร")
    out += [f"Copyright ({len(line.copyright)}/{COPYRIGHT_MAX})", line.copyright]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return notes


def build(theme, *, include_other_themes=False, log=print):
    if theme.lettering:
        from .compose import compose
        compose(theme, log=log)   # source/ is always re-typed from art/ so caption edits show up
    nums = _source_numbers(theme)
    if not nums:
        raise ThemeError(f"No source/NN.png in {theme.source_dir}")
    too_big = [n for n in nums if n > theme.count]
    if too_big:
        raise ThemeError(f"source has numbers above count={theme.count}: {too_big}")
    gaps = [n for n in range(1, nums[-1] + 1) if n not in nums]
    if gaps:
        raise ThemeError(f"source/ must be numbered 01..NN without gaps; missing {gaps}")
    if theme.main not in nums:
        raise ThemeError(f"main sticker {theme.main:02d}.png does not exist yet")

    from .duplicates import check_duplicates
    # Validate before deleting or writing any previously exported files.
    check_duplicates(theme, include_other_themes=include_other_themes)

    notes = []
    out = theme.dist_dir / "line_upload"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()

    sticker_box = BIG_STICKER if theme.export_type == "big" else STICKER
    sticker_margin = 2 if theme.export_type == "big" else MARGIN
    rendered = []
    for n in nums:
        src = clean(Image.open(theme.source_path(n)))
        if not is_background_transparent(src):
            notes.append(f"{n:02d}.png: พื้นหลังดูเหมือนไม่ใส")
        im = fit(src, sticker_box, sticker_margin)
        if theme.export_type == "big":
            bbox = im.getchannel("A").getbbox()
            if not bbox or bbox[3] - bbox[1] < BIG_MIN_ART_HEIGHT:
                fix = ("art/{0:02d}.png is too wide: regenerate it as portrait (3:4) full-body art "
                       "(generate {1} --only {0} --force), or split the caption into 2 lines with \\n"
                       if theme.lettering else
                       "redesign as a tall composition instead of adding empty padding").format(n, theme.id)
                raise ThemeError(f"{n:02d}.png: Big sticker artwork must fill at least 524px in height; {fix}")
        name = f"{n:02d}.png"
        if save_png(im, out / name) > MAX_BYTES:
            notes.append(f"{name} ใหญ่เกิน 1 MB")
        rendered.append((n, im))

    # main/tab show the character; with code lettering use the text-free art.
    main_src = theme.source_path(theme.main)
    if theme.lettering and theme.art_path(theme.main).exists():
        main_src = theme.art_path(theme.main)
    base = clean(Image.open(main_src))
    save_png(fit(base, MAIN, 4), out / "main.png")
    tab_src = base.crop(theme.tab_crop) if theme.tab_crop else base
    save_png(fit(tab_src, TAB, 2), out / "tab.png")

    zip_path = theme.dist_dir / f"{theme.id}-line.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ["main.png", "tab.png"] + [f"{n:02d}.png" for n in nums]:
            z.write(out / name, name)

    preview_path = theme.dist_dir / "preview.png"
    _preview(rendered, preview_path, cell=sticker_box)

    notes += _listing(theme, theme.dist_dir / "line_info.txt")
    (theme.dist_dir / "upload_type.txt").write_text(
        ("LINE Creators Market: select Big Stickers (บิ๊กสติกเกอร์).\n"
         "Sticker PNG: 396 x 660 px, transparent. LINE adds its own outer margin.\n"
         if theme.export_type == "big" else
         "LINE Creators Market: select Stickers (สติกเกอร์).\n"), encoding="utf-8")
    if len(nums) < theme.count:
        notes.append(f"ยังไม่ครบชุด: {len(nums)}/{theme.count} ภาพ")
    if len(nums) not in VALID_COUNTS:
        notes.append(f"LINE รับชุดละ {VALID_COUNTS} ภาพ ตอนนี้มี {len(nums)} ภาพ")
    return BuildResult(zip_path=zip_path, preview_path=preview_path, count=len(nums), notes=notes)
