import shutil

import pytest
from PIL import Image

from conftest import sticker_image
from studio.build import build
from studio.duplicates import check_duplicates, text_key
from studio.theme import ThemeError


def test_thai_layout_punctuation_and_invisible_spaces_are_not_new_phrases():
    assert text_key("รอ\nแป๊บ!") == text_key("รอ แป๊บ\u200b")
    assert text_key("ได้") != text_key("ได")  # Never discard tone marks.


def test_reject_duplicate_text_before_generation(make_theme):
    with pytest.raises(ThemeError, match="คำพูดซ้ำ.*01 / 02"):
        make_theme(stickers=[{"n": 1, "text": "ขอบคุณครับ"},
                             {"n": 2, "text": "ขอบคุณ\nครับ!"}])


def test_reject_duplicate_pose_descriptions(make_theme):
    with pytest.raises(ThemeError, match="ท่าทางซ้ำ"):
        make_theme(stickers=[{"n": 1, "text": "หนึ่ง", "pose": "Wave hello!"},
                             {"n": 2, "text": "สอง", "pose": "wave\nhello"}])


def test_duplicate_image_rejection_preserves_old_export(make_theme):
    t = make_theme()
    sticker_image(t.source_path(1))
    shutil.copyfile(t.source_path(1), t.source_path(2))
    old = t.dist_dir / "line_upload" / "01.png"
    old.parent.mkdir(parents=True)
    old.write_bytes(b"previous export")
    with pytest.raises(ThemeError, match="ภาพซ้ำ.*01.png.*02.png"):
        build(t)
    assert old.read_bytes() == b"previous export"
    assert not list(t.dist_dir.glob("*.zip"))


def test_padding_and_hidden_rgb_do_not_hide_reused_art(make_theme):
    t = make_theme()
    original = sticker_image(t.source_path(1))
    with Image.open(original) as im:
        padded = Image.new("RGBA", (900, 800), (100, 20, 70, 0))
        padded.paste(im, (50, 100))
        padded.save(t.source_path(2))
    with pytest.raises(ThemeError, match="ภาพซ้ำ"):
        check_duplicates(t)


def test_different_captions_cannot_hide_reused_text_free_art(make_theme):
    t = make_theme()
    sticker_image(t.dir / "art" / "01.png")
    shutil.copyfile(t.dir / "art" / "01.png", t.dir / "art" / "02.png")
    with pytest.raises(ThemeError, match="art/01.png.*art/02.png"):
        check_duplicates(t)


def test_cross_theme_check_reports_old_phrase_and_image(make_theme):
    t = make_theme()
    sticker_image(t.source_path(1))
    other = t.dir.parent / "old-cat"
    (other / "source").mkdir(parents=True)
    (other / "theme.yaml").write_text('stickers: [{n: 8, text: "คำ1!"}]', encoding="utf-8")
    shutil.copyfile(t.source_path(1), other / "source" / "08.png")
    check_duplicates(t)  # Local scope remains useful for existing revisions.
    with pytest.raises(ThemeError) as exc:
        check_duplicates(t, include_other_themes=True)
    assert "คำพูดซ้ำข้ามชุด" in str(exc.value)
    assert "ภาพซ้ำข้ามชุด" in str(exc.value)
    assert "old-cat" in str(exc.value)


def test_distinct_images_and_text_free_stickers_are_allowed(make_theme):
    t = make_theme(stickers=[{"n": 1, "text": ""}, {"n": 2, "text": ""}])
    sticker_image(t.source_path(1), color=(255, 0, 0, 255))
    sticker_image(t.source_path(2), color=(0, 0, 255, 255))
    check_duplicates(t)


def test_build_can_check_older_themes(make_theme):
    t = make_theme()
    sticker_image(t.source_path(1))
    other = t.dir.parent / "previous"
    other.mkdir()
    (other / "theme.yaml").write_text('stickers: [{n: 1, text: "คำ1"}]', encoding="utf-8")
    with pytest.raises(ThemeError, match="คำพูดซ้ำข้ามชุด"):
        build(t, include_other_themes=True)
    assert not t.dist_dir.exists()
    # Everyday phrases may repeat across different sets by default.
    assert build(t).count == 1


@pytest.mark.parametrize("flag, expected", [(None, False), ("--within-set", False),
                                           ("--all-themes", True)])
def test_cli_scope_default_and_explicit_choice(make_theme, monkeypatch, flag, expected):
    from studio import cli

    t = make_theme()
    monkeypatch.setattr(cli, "resolve", lambda _: t.dir)
    monkeypatch.setattr(cli, "load_theme", lambda _: t)
    scopes = []
    monkeypatch.setattr(cli, "check_duplicates",
                        lambda theme, *, include_other_themes: scopes.append(include_other_themes))
    cli.main(["check", t.id] + ([flag] if flag else []))
    assert scopes == [expected]
