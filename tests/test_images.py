from PIL import Image, ImageDraw

from studio.images import clean, is_background_transparent, remove_background


def test_clean_snaps_alpha_and_whitens_hidden_rgb():
    im = Image.new("RGBA", (3, 1))
    im.putpixel((0, 0), (10, 20, 30, 240))   # gpt-image "almost opaque" art
    im.putpixel((1, 0), (10, 20, 30, 120))   # real anti-aliased edge
    im.putpixel((2, 0), (200, 0, 0, 5))      # noise with a hidden colour
    out = clean(im)
    assert out.getpixel((0, 0)) == (10, 20, 30, 255)
    assert out.getpixel((1, 0)) == (10, 20, 30, 120)
    assert out.getpixel((2, 0)) == (255, 255, 255, 0)


def _sticker_on(bg_fill):
    """Orange disc with a dark outline and a white die-cut ring, on an opaque background."""
    im = Image.new("RGBA", (500, 500), bg_fill)
    d = ImageDraw.Draw(im)
    d.ellipse((90, 90, 410, 410), fill=(255, 255, 255, 255))                       # die-cut ring
    d.ellipse((110, 110, 390, 390), fill=(240, 120, 30, 255), outline=(20, 20, 40, 255), width=8)
    d.ellipse((220, 220, 280, 280), fill=(255, 255, 255, 255), outline=(20, 20, 40, 255), width=6)
    return im


def test_remove_white_background_keeps_enclosed_white_and_redraws_border():
    out, why = remove_background(_sticker_on((255, 255, 255, 255)))
    assert why is None
    assert is_background_transparent(out)
    assert out.getpixel((250, 250)) == (255, 255, 255, 255)      # white inside the outline survives
    assert out.getpixel((250, 150))[:3] == (240, 120, 30)
    r, g, b, a = out.getpixel((250, 104))                        # border just outside the outline
    assert (r, g, b) == (255, 255, 255) and a >= 250
    assert out.getpixel((250, 40))[3] == 0


def test_remove_checkered_background():
    im = _sticker_on((255, 255, 255, 255))
    px = im.load()
    for y in range(500):
        for x in range(500):
            if px[x, y] == (255, 255, 255, 255) and (x // 25 + y // 25) % 2 and (x - 250) ** 2 + (y - 250) ** 2 > 165 ** 2:
                px[x, y] = (204, 204, 204, 255)
    out, why = remove_background(im)
    assert why is None
    assert is_background_transparent(out)


def test_coloured_background_is_not_touched():
    im = _sticker_on((40, 160, 60, 255))
    out, why = remove_background(im)
    assert why is not None
    assert out.getpixel((0, 0)) == (40, 160, 60, 255)
