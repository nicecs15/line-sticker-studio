"""Code lettering: text-free art/NN.png + caption typed with a font -> source/NN.png.

The result is a tight composite at high resolution; build then scales it into the LINE box.
"""
from PIL import Image

from .images import clean
from .lettering import FONT_SIZE, render_caption
from .theme import ThemeError

# Composite canvas (about 2x the LINE box, so build only ever scales down).
CANVAS = {"regular": (740, 640), "big": (792, 1320)}
TEXT_SHARE = {"regular": 0.36, "big": 0.40}   # max share of the height the caption may take
OVERLAP = 0.10                                # caption overlaps the art by this share of its height


def _trim(im):
    bbox = im.getchannel("A").getbbox()
    if bbox is None:
        raise ThemeError("image is fully transparent")
    return im.crop(bbox)


def _scale(im, max_w, max_h):
    s = min(max_w / im.width, max_h / im.height)
    return im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)


def caption_color(theme, sticker):
    colors = theme.lettering.colors
    return sticker.color or colors[(sticker.n - 1) % len(colors)]


def compose_one(theme, sticker):
    lt = theme.lettering
    art = _trim(clean(Image.open(theme.art_path(sticker.n))))
    w, h = CANVAS[theme.export_type]
    if not sticker.text.strip():
        return _scale(art, w, h)

    text = render_caption(sticker.text, lt.font, caption_color(theme, sticker), lt.outline, FONT_SIZE)
    text = _scale(text, w, h * TEXT_SHARE[theme.export_type])
    overlap = round(text.height * OVERLAP)
    art = _scale(art, w, h - text.height + overlap)

    out = Image.new("RGBA", (max(text.width, art.width), text.height + art.height - overlap), (0, 0, 0, 0))
    tx = (out.width - text.width) // 2
    ax = (out.width - art.width) // 2
    if lt.position == "top":
        out.alpha_composite(art, (ax, text.height - overlap))
        out.alpha_composite(text, (tx, 0))
    else:
        out.alpha_composite(art, (ax, 0))
        out.alpha_composite(text, (tx, art.height - overlap))
    return out


def compose(theme, numbers=None, log=print):
    """Write source/NN.png for every art/NN.png (or just `numbers`). Returns the numbers written."""
    if not theme.lettering:
        raise ThemeError(f"{theme.id} has no 'lettering:' in theme.yaml; captions are drawn by the image model")
    numbers = numbers or [n for n in range(1, theme.count + 1) if theme.art_path(n).exists()]
    theme.source_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for n in numbers:
        sticker = theme.sticker(n)
        if sticker is None:
            log(f"  {n:02d}: no caption drafted in theme.yaml, skipped")
            continue
        if not theme.art_path(n).exists():
            log(f"  {n:02d}: art/{n:02d}.png missing, skipped")
            continue
        compose_one(theme, sticker).save(theme.source_path(n), "PNG")
        written.append(n)
    return written
