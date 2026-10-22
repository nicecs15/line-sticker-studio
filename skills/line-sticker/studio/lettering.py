"""Render sticker captions with a real font so Thai vowels and tone marks are always correct.

Image models often misspell Thai, and Pillow on Windows ships without libraqm (no Thai shaping).
HarfBuzz (uharfbuzz) places the glyphs; this module rasterizes their outlines with Pillow and
adds the sticker look: coloured letters, dark outline, thick white edge and a soft shadow.
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from .theme import DEFAULT_COLORS, DEFAULT_FONT, DEFAULT_OUTLINE, ROOT, ThemeError

FONTS_DIR = ROOT / "fonts"
FONT_SIZE = 220        # px per em; build scales the finished sticker down, so render big
CURVE_STEPS = 10       # line segments per Bezier curve
LINE_GAP = 0.06        # em between the ink of two caption lines


class _Pen:
    """fontTools-style pen that HarfBuzz draws into; collects flattened contours."""

    def __init__(self):
        self.contours, self._cur = [], None

    def moveTo(self, p):
        self._cur = [p]

    def lineTo(self, p):
        self._cur.append(p)

    def qCurveTo(self, *pts):
        # TrueType allows several off-curve points with implied on-curve midpoints.
        start = self._cur[-1]
        offs, end = list(pts[:-1]), pts[-1]
        for i, c in enumerate(offs):
            nxt = end if i == len(offs) - 1 else ((c[0] + offs[i + 1][0]) / 2, (c[1] + offs[i + 1][1]) / 2)
            for s in range(1, CURVE_STEPS + 1):
                t = s / CURVE_STEPS
                u = 1 - t
                self._cur.append((u * u * start[0] + 2 * u * t * c[0] + t * t * nxt[0],
                                  u * u * start[1] + 2 * u * t * c[1] + t * t * nxt[1]))
            start = nxt

    def curveTo(self, c1, c2, p):
        p0 = self._cur[-1]
        for s in range(1, CURVE_STEPS + 1):
            t = s / CURVE_STEPS
            u = 1 - t
            self._cur.append(tuple(u ** 3 * p0[k] + 3 * u * u * t * c1[k] + 3 * u * t * t * c2[k] + t ** 3 * p[k]
                                   for k in (0, 1)))

    def closePath(self):
        if self._cur and len(self._cur) > 2:
            self.contours.append(self._cur)
        self._cur = None

    endPath = closePath


def font_path(name=DEFAULT_FONT):
    """'Kanit-ExtraBold' -> fonts/Kanit-ExtraBold.ttf; a path to a .ttf/.otf works too."""
    p = Path(name)
    candidates = [p] if p.suffix else [FONTS_DIR / f"{name}.ttf", FONTS_DIR / f"{name}.otf"]
    for c in candidates:
        if c.exists():
            return c
    known = ", ".join(sorted(f.stem for f in FONTS_DIR.glob("*.[ot]tf"))) or "(none)"
    raise ThemeError(f"font '{name}' not found in {FONTS_DIR} (available: {known})")


def _hb():
    try:
        import uharfbuzz
    except ImportError:
        raise ThemeError(f"uharfbuzz is missing: python -m pip install -r \"{ROOT / 'requirements.txt'}\"")
    return uharfbuzz


def _shape_line(font, text, scale):
    """Return [(contours in px, y down from baseline)] for one line and its advance width."""
    hb = _hb()
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {})
    glyphs, x = [], 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = _Pen()
        font.draw_glyph_with_pen(info.codepoint, pen)
        ox, oy = x + pos.x_offset, pos.y_offset
        glyphs.append([[((ox + px) * scale, -(oy + py) * scale) for px, py in c] for c in pen.contours])
        x += pos.x_advance
    return glyphs, x * scale


def caption_lines(text):
    """Split on explicit newlines; otherwise balance on spaces. Thai words are never cut."""
    lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    if len(lines) == 1 and " " in lines[0] and len(lines[0]) > 10:
        words = lines[0].split()
        best = min(range(1, len(words)),
                   key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
        lines = [" ".join(words[:best]), " ".join(words[best:])]
    return lines


def text_mask(text, font_name=DEFAULT_FONT, size=FONT_SIZE):
    """Hard-edged L mask of the caption (lines centred), cropped to the ink."""
    hb = _hb()
    face = hb.Face(hb.Blob.from_file_path(str(font_path(font_name))))
    font = hb.Font(face)
    scale = size / face.upem

    shaped = []
    for line in caption_lines(text):
        glyphs, width = _shape_line(font, line, scale)
        ys = [p[1] for g in glyphs for c in g for p in c] or [0]
        shaped.append((glyphs, width, min(ys), max(ys)))
    if not shaped:
        raise ThemeError("caption is empty")

    pad = int(size * 0.1)
    width = int(max(w for _, w, _, _ in shaped)) + 2 * pad
    baselines, y = [], pad
    for i, (_, _, top, bottom) in enumerate(shaped):
        y += -top if i == 0 else (shaped[i - 1][3] - top + LINE_GAP * size)
        baselines.append(y)
    height = int(baselines[-1] + shaped[-1][3]) + pad

    mask = Image.new("L", (width, height), 0)
    for (glyphs, line_w, _, _), base in zip(shaped, baselines):
        dx = (width - line_w) / 2
        for contours in glyphs:
            pts = [(px + dx, py + base) for c in contours for px, py in c]
            if not pts:
                continue
            x0, y0 = int(min(p[0] for p in pts)) - 1, int(min(p[1] for p in pts)) - 1
            x1, y1 = int(max(p[0] for p in pts)) + 2, int(max(p[1] for p in pts)) + 2
            # Even-odd fill per glyph (XOR of contours) keeps the counters of letters open;
            # glyphs are then OR-ed so marks overlapping their base letter stay solid.
            glyph = Image.new("1", (x1 - x0, y1 - y0), 0)
            for c in contours:
                one = Image.new("1", glyph.size, 0)
                ImageDraw.Draw(one).polygon([(px + dx - x0, py + base - y0) for px, py in c], fill=1)
                glyph = ImageChops.logical_xor(glyph, one)
            mask.paste(255, (x0, y0), glyph)
    return mask.crop(mask.getbbox())


def _grow(mask, radius):
    """Dilate a mask by ~radius px with rounded corners (blur + low threshold)."""
    if radius < 1:
        return mask
    return mask.filter(ImageFilter.GaussianBlur(radius / 2)).point(lambda v: 255 if v > 6 else 0)


def render_caption(text, font_name=DEFAULT_FONT, color=DEFAULT_COLORS[0], outline=DEFAULT_OUTLINE,
                   size=FONT_SIZE):
    """RGBA sticker lettering: shadow, white edge, dark outline, coloured letters."""
    letters = text_mask(text, font_name, size)
    edge_r, outline_r = round(size * 0.13), round(size * 0.045)
    pad = edge_r + round(size * 0.08)
    w, h = letters.width + 2 * pad, letters.height + 2 * pad
    fill = Image.new("L", (w, h), 0)
    fill.paste(letters, (pad, pad))

    dark = _grow(fill, outline_r)
    white = _grow(dark, edge_r - outline_r)
    shadow = Image.new("L", (w, h), 0)
    off = round(size * 0.04)
    shadow.paste(white.crop((0, 0, w - off, h - off)), (off, off))
    shadow = shadow.filter(ImageFilter.GaussianBlur(size * 0.015)).point(lambda v: v * 45 // 100)

    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for layer_mask, rgb in ((shadow, outline), (white, "#FFFFFF"), (dark, outline), (fill, color)):
        layer = Image.new("RGBA", (w, h), rgb)
        layer.putalpha(layer_mask)
        out.alpha_composite(layer)
    return out.crop(out.getchannel("A").getbbox())
