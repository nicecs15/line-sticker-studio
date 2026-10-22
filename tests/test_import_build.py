import zipfile

import pytest
from PIL import Image

from conftest import sticker_image, touch_mtime
from studio.build import build
from studio.importer import import_images
from studio.theme import ThemeError


def test_import_fills_missing_numbers_oldest_first(make_theme):
    t = make_theme(count=8)
    sticker_image(t.source_path(1))
    newer = sticker_image(t.inbox_dir / "a.png")
    older = sticker_image(t.inbox_dir / "b.png")
    touch_mtime(newer, 2_000_000_000)
    touch_mtime(older, 1_000_000_000)

    r = import_images(t)

    assert r.imported == [("b.png", 2), ("a.png", 3)]
    assert t.done() == [1, 2, 3]
    assert sorted(p.name for p in (t.inbox_dir / "_imported").iterdir()) == ["a.png", "b.png"]
    assert not (t.inbox_dir / "a.png").exists()


def test_import_reports_leftovers_and_opaque_background(make_theme):
    t = make_theme(count=8)
    for n in range(1, 8):
        sticker_image(t.source_path(n))
    sticker_image(t.inbox_dir / "x.png", transparent=False)
    sticker_image(t.inbox_dir / "y.png")
    touch_mtime(t.inbox_dir / "y.png", 2_000_000_000)

    r = import_images(t)

    assert r.imported == [("x.png", 8)]
    assert r.leftover == ["y.png"]
    assert "ลบพื้นหลังขาว/ลายตารางให้อัตโนมัติแล้ว" in r.warnings[0]
    assert Image.open(t.source_path(8)).getpixel((0, 0))[3] == 0


def test_import_keep_bg_and_coloured_background_are_left_alone(make_theme):
    t = make_theme(count=8)
    sticker_image(t.inbox_dir / "white.png", transparent=False)
    r = import_images(t, keep_bg=True)
    assert "--keep-bg" in r.warnings[0]
    assert Image.open(t.source_path(1)).getpixel((0, 0)) == (255, 255, 255, 255)

    green = Image.new("RGBA", (400, 400), (40, 160, 60, 255))
    green.save(t.inbox_dir / "green.png")
    r = import_images(t)
    assert "ลบอัตโนมัติไม่ได้" in r.warnings[0]
    assert Image.open(t.source_path(2)).getpixel((0, 0)) == (40, 160, 60, 255)


def test_import_as_replaces_and_keeps_old(make_theme):
    t = make_theme(count=8)
    sticker_image(t.source_path(4), color=(0, 0, 255, 255))
    sticker_image(t.inbox_dir / "redo.png", color=(255, 0, 0, 255))

    r = import_images(t, as_number=4)

    assert r.imported == [("redo.png", 4)]
    assert Image.open(t.source_path(4)).getpixel((300, 250))[:3] == (255, 0, 0)
    assert (t.inbox_dir / "_replaced" / "04-04.png").exists()


def test_build_outputs_line_pack(make_theme):
    t = make_theme(count=8, tab_crop=[100, 80, 500, 300],
                   line={"copyright": "S", "en": {"title": "T", "description": "D"}})
    for n in range(1, 9):
        sticker_image(t.source_path(n), color=(20*n, 120, 30, 255))

    r = build(t)

    up = t.dist_dir / "line_upload"
    assert Image.open(up / "01.png").size == (370, 320)
    assert Image.open(up / "main.png").size == (240, 240)
    assert Image.open(up / "tab.png").size == (96, 74)
    names = zipfile.ZipFile(r.zip_path).namelist()
    assert names == ["main.png", "tab.png"] + [f"{n:02d}.png" for n in range(1, 9)]
    assert r.preview_path.exists()
    assert r.notes == []


def test_build_partial_set_adds_notes(make_theme):
    t = make_theme(count=16)
    for n in range(1, 5):
        sticker_image(t.source_path(n), color=(20*n, 120, 30, 255))
    r = build(t)
    assert r.count == 4
    assert any("4/16" in note for note in r.notes)


def test_build_rejects_gaps(make_theme):
    t = make_theme(count=8)
    sticker_image(t.source_path(1))
    sticker_image(t.source_path(3))
    with pytest.raises(ThemeError, match=r"missing \[2\]"):
        build(t)


def test_build_writes_line_listing_and_checks_limits(make_theme):
    t = make_theme(count=8, line={
        "copyright": "Studio",
        "en": {"title": "Test Cat", "description": "A tiny orange cat."},
        "th": {"title": "แมวทดสอบ", "description": "x" * 161},
    })
    for n in range(1, 9):
        sticker_image(t.source_path(n), color=(20*n, 120, 30, 255))

    r = build(t)

    info = (t.dist_dir / "line_info.txt").read_text(encoding="utf-8")
    assert "Test Cat" in info and "แมวทดสอบ" in info and "Studio" in info
    assert r.notes == ["LINE th description ยาว 161/160 ตัวอักษร"]


def test_build_without_line_listing_adds_note(make_theme):
    t = make_theme(count=8)
    for n in range(1, 9):
        sticker_image(t.source_path(n), color=(20*n, 120, 30, 255))
    r = build(t)
    assert not (t.dist_dir / "line_info.txt").exists()
    assert any("line:" in note for note in r.notes)


def test_big_pack_uses_large_portrait_artwork(make_theme):
    from PIL import ImageDraw

    t = make_theme(count=8, export_type="big",
                   line={"copyright": "S", "en": {"title": "T", "description": "D"}})
    t.source_dir.mkdir(parents=True, exist_ok=True)
    for n in range(1, 9):
        im = Image.new("RGBA", (400, 700))
        ImageDraw.Draw(im).rounded_rectangle((20, 20, 380, 680), radius=30,
                                             fill=(20*n, 120, 30, 255))
        im.save(t.source_path(n))
    r = build(t)
    with Image.open(t.dist_dir / "line_upload" / "01.png") as im:
        assert im.size == (396, 660)
        bbox = im.getchannel("A").getbbox()
        assert bbox[3] - bbox[1] >= 524
    assert r.notes == []
    assert "Big Stickers" in (t.dist_dir / "upload_type.txt").read_text(encoding="utf-8")
    assert len(zipfile.ZipFile(r.zip_path).namelist()) == 10


def test_big_pack_rejects_short_artwork_with_empty_padding(make_theme):
    t = make_theme(count=8, export_type="big")
    sticker_image(t.source_path(1))
    with pytest.raises(ThemeError, match="redesign as a tall composition"):
        build(t)
