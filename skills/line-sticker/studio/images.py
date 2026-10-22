"""Small Pillow helpers shared by import / build / generate."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ALPHA_NOISE = 8        # alpha <= this is treated as fully transparent
ALPHA_SOLID = 230      # gpt-image art comes out ~95% opaque; alpha >= this becomes fully opaque
MAX_BYTES = 1024 * 1024

# Background removal: a pixel is "background-like" if it is light and nearly grey
# (white, or the light-grey squares of a fake checkerboard).
BG_MIN_LIGHT = 200
BG_MAX_CHROMA = 30
BORDER_RATIO = 0.016   # re-drawn white die-cut border, as a fraction of the image's short side


def clean(im):
    """Snap alpha (noise -> 0, near-opaque -> 255) and whiten RGB under transparent pixels."""
    im = im.convert("RGBA")
    a = np.array(im)
    alpha = a[..., 3]
    alpha[alpha <= ALPHA_NOISE] = 0
    alpha[alpha >= ALPHA_SOLID] = 255
    a[alpha == 0, :3] = 255
    return Image.fromarray(a, "RGBA")


def is_background_transparent(im, patch=6):
    """True when all four corners are transparent - ChatGPT often returns white/checkered backgrounds."""
    a = im.convert("RGBA").getchannel("A")
    w, h = a.size
    p = min(patch, w, h)
    for x, y in ((0, 0), (w - p, 0), (0, h - p), (w - p, h - p)):
        if a.crop((x, y, x + p, y + p)).getextrema()[1] > ALPHA_NOISE:
            return False
    return True


def _background_mask(im):
    """L mask (255 = background) of light, greyish pixels connected to the image border."""
    rgb = np.array(im.convert("RGB")).astype(np.int16)
    light = rgb.min(axis=2) >= BG_MIN_LIGHT
    grey = (rgb.max(axis=2) - rgb.min(axis=2)) <= BG_MAX_CHROMA
    # .copy(): fromarray shares the numpy buffer read-only, and floodfill must write in place
    cand = Image.fromarray(np.where(light & grey, 255, 0).astype(np.uint8), "L").copy()
    w, h = cand.size
    px = cand.load()
    border = ([(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)]
              + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)])
    for xy in border:
        if px[xy] == 255:
            ImageDraw.floodfill(cand, xy, 128)
    return cand.point(lambda v: 255 if v == 128 else 0)


def remove_background(im):
    """Cut away a white / checkered background and re-draw the white die-cut border.

    Returns (image, None) on success or (original image, reason) when it is not safe to cut,
    e.g. a coloured background or a cut that would remove almost everything.
    """
    im = im.convert("RGBA")
    bg = _background_mask(im)
    removed = np.array(bg).mean() / 255
    if removed < 0.05:
        return im, "พื้นหลังไม่ใช่สีขาว/ลายตาราง ลบอัตโนมัติไม่ได้"
    if removed > 0.92:
        return im, "ลบพื้นหลังแล้วแทบไม่เหลือภาพ จึงไม่ลบ"

    art = im.copy()
    art_alpha = Image.fromarray(np.minimum(np.array(im.getchannel("A")), 255 - np.array(bg)), "L")
    art.putalpha(art_alpha)

    # Die-cut border: grow the art silhouette by ~r px (blur + low threshold gives rounded corners).
    r = max(2, round(min(im.size) * BORDER_RATIO))
    solid = art_alpha.point(lambda v: 255 if v > 128 else 0)
    grown = solid.filter(ImageFilter.GaussianBlur(r / 2)).point(lambda v: 255 if v > 6 else 0)
    grown = grown.filter(ImageFilter.GaussianBlur(1))
    out = Image.new("RGBA", im.size, (255, 255, 255, 0))
    out.putalpha(grown)
    out.alpha_composite(art)
    return out, None


def fit(im, box, margin):
    """Trim transparent border, scale to fit box minus margin, center on transparent canvas."""
    bbox = im.getchannel("A").getbbox()
    if bbox:
        im = im.crop(bbox)
    max_w, max_h = box[0] - 2 * margin, box[1] - 2 * margin
    scale = min(max_w / im.width, max_h / im.height)
    size = (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
    im = im.resize(size, Image.LANCZOS, reducing_gap=3.0)
    canvas = Image.new("RGBA", box, (0, 0, 0, 0))
    canvas.alpha_composite(im, ((box[0] - size[0]) // 2, (box[1] - size[1]) // 2))
    return canvas


def save_png(im, path):
    """Save as optimized 72dpi PNG; return file size in bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "PNG", optimize=True, dpi=(72, 72))
    return path.stat().st_size
