import zipfile

import numpy as np
import pytest
import yaml
from PIL import Image

from conftest import sticker_image
from studio.build import build
from studio.compose import compose
from studio.importer import import_images
from studio.lettering import caption_lines, render_caption, text_mask
from studio.prompts import sticker_prompt
from studio.scaffold import new_theme
from studio.theme import ThemeError, load_theme


def test_caption_lines_keep_thai_words_whole():
    assert caption_lines("ขอบคุณ\nจากใจ") == ["ขอบคุณ", "จากใจ"]
    assert caption_lines("สวัสดีครับ") == ["สวัสดีครับ"]
    assert caption_lines("ทำงาน วันนี้ เหนื่อยมาก") == ["ทำงาน วันนี้", "เหนื่อยมาก"]


def test_thai_marks_are_drawn_above_the_letters():
    base = text_mask("นน")
    marked = text_mask("นี่นี่")   # sara i + mai ek stack above the consonant
    assert marked.height > base.height * 1.3
    assert abs(marked.width - base.width) < base.width * 0.25


def test_render_caption_has_white_edge_and_colour():
    im = render_caption("สู้ๆ", color="#FF0000")
    assert im.mode == "RGBA" and im.width > im.height
    a = np.array(im)
    colours = {tuple(px[:3]) for px in a[a[..., 3] == 255]}
    assert (255, 255, 255) in colours and (255, 0, 0) in colours


def test_lettering_settings_are_validated(make_theme):
    t = make_theme(lettering=True)
    assert t.lettering.font == "Kanit-ExtraBold" and t.lettering.position == "top"
    with pytest.raises(ThemeError, match="font 'Nope'"):
        make_theme(lettering={"font": "Nope"})
    with pytest.raises(ThemeError, match="position"):
        make_theme(lettering={"position": "left"})
    with pytest.raises(ThemeError, match="not a colour"):
        make_theme(lettering={"colors": ["blue-ish"]})


def test_lettering_mode_imports_into_art_and_prompts_ask_for_no_text(make_theme):
    t = make_theme(lettering=True)
    sticker_image(t.inbox_dir / "x.png")
    import_images(t)
    assert t.art_path(1).exists() and not t.source_path(1).exists()
    assert t.done() == [1]
    prompt = sticker_prompt(t, t.sticker(2), False)
    assert "NO text" in prompt and "do NOT write it" in prompt and "exact spelling" not in prompt


def test_numbered_inbox_files_go_to_their_slot(make_theme):
    t = make_theme(count=8)
    sticker_image(t.inbox_dir / "05.png")
    sticker_image(t.inbox_dir / "07-wave.png")
    sticker_image(t.inbox_dir / "chatgpt.png")
    r = import_images(t)
    assert sorted(n for _, n in r.imported) == [1, 5, 7]
    assert t.done() == [1, 5, 7]


@pytest.mark.parametrize("position", ["top", "bottom"])
def test_compose_puts_caption_above_or_below_art(make_theme, position):
    t = make_theme(count=8, lettering={"position": position, "colors": ["#FF0000"]})
    sticker_image(t.art_path(1), color=(0, 0, 255, 255))
    assert compose(t, log=lambda *_: None) == [1]
    im = Image.open(t.source_path(1)).convert("RGBA")
    top = np.array(im.crop((0, 0, im.width, im.height // 4)))
    red_on_top = bool(((top[..., 0] == 255) & (top[..., 1] == 0) & (top[..., 3] == 255)).any())
    assert red_on_top == (position == "top")


def test_build_with_lettering_types_captions_and_uses_art_for_main(make_theme):
    t = make_theme(count=8, lettering=True, line={"copyright": "S", "en": {"title": "T", "description": "D"}})
    for n in range(1, 9):
        sticker_image(t.art_path(n), color=(20 * n, 120, 30, 255))
    r = build(t, log=lambda *_: None)
    assert sorted(p.name for p in t.source_dir.iterdir()) == [f"{n:02d}.png" for n in range(1, 9)]
    assert len(zipfile.ZipFile(r.zip_path).namelist()) == 10
    assert r.notes == []


def test_new_theme_template_loads(tmp_path):
    path = new_theme("cat-accountant", count=24, themes_dir=tmp_path)
    t = load_theme(path.parent)
    assert t.count == 24 and t.export_type == "big" and t.lettering is not None
    assert t.sticker(1).text == "สวัสดี\nครับ"
    with pytest.raises(ThemeError, match="already exists"):
        new_theme("cat-accountant", themes_dir=tmp_path)
    with pytest.raises(ThemeError, match="lowercase"):
        new_theme("Cat Accountant", themes_dir=tmp_path)
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["style"] == "clean-art"


def test_literal_backslash_n_is_a_line_break(make_theme):
    t = make_theme(count=8, stickers=[{"n": 1, "text": r"ขอบคุณ\nครับ", "pose": "wai"}])
    assert t.sticker(1).text == "ขอบคุณ\nครับ"
    assert t.sticker(1).label == "ขอบคุณ / ครับ"
