import pytest
import yaml

from conftest import sticker_image
from studio.prompts import render_prompts_md, sticker_prompt
from studio.theme import ThemeError, load_theme


def test_progress_tracks_source_files(make_theme):
    t = make_theme(count=8)
    sticker_image(t.source_path(1))
    sticker_image(t.source_path(3))
    assert t.done() == [1, 3]
    assert t.missing() == [2, 4, 5, 6, 7, 8]


def test_undrafted(make_theme):
    t = make_theme(count=8, drafted=[1, 2, 5])
    assert t.undrafted() == [3, 4, 6, 7, 8]


@pytest.mark.parametrize("patch, msg", [
    ({"count": 10}, "count must be one of"),
    ({"stickers": [{"n": 1, "text": "a"}, {"n": 1, "text": "b"}]}, "defined twice"),
    ({"stickers": [{"n": 9, "text": "a"}]}, "outside 1..8"),
    ({"character": ""}, "missing 'character'"),
    ({"style": "nope"}, "style 'nope' not found"),
])
def test_invalid_theme(make_theme, patch, msg):
    t = make_theme(count=8)
    path = t.dir / "theme.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data.update(patch)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ThemeError, match=msg):
        load_theme(t.dir, style_dir=t.dir.parent.parent / "style")


def test_sticker_prompt_contains_all_parts(make_theme):
    t = make_theme(count=8)
    p = sticker_prompt(t, t.sticker(2), with_reference=True)
    for part in ["attached reference image", "a tiny orange cat", "STYLE-LOCK line",
                 "Pose: pose 2", "Props: props 2", 'Text (exact spelling): "คำ2". Layout: style 2']:
        assert part in p
    assert "attached reference" not in sticker_prompt(t, t.sticker(2), with_reference=False)


def test_prompts_md_lists_todo_before_done(make_theme):
    t = make_theme(count=8, drafted=range(1, 7))
    sticker_image(t.source_path(1))
    md = render_prompts_md(t)
    assert "**1/8**" in md
    assert "ยังไม่ได้ร่างคำพูด: 07, 08" in md
    assert md.index("### ⬜ 02") < md.index("### ✅ 01")
    assert "| 07 | (ยังไม่ได้ร่าง) | ⬜ |" in md
    assert "ยังไม่มีภาพอ้างอิง" in md


def test_big_theme_prompts_require_tall_readable_composition(make_theme):
    t = make_theme(count=8, export_type="big")
    prompt = sticker_prompt(t, t.sticker(1), with_reference=False)
    assert "396 x 660" in prompt
    assert "short readable lines" in prompt


def test_unknown_export_type_is_rejected(make_theme):
    with pytest.raises(ThemeError, match="export_type must be regular or big"):
        make_theme(count=8, export_type="huge")


def test_theme_yaml_with_bom_loads(make_theme):
    # Windows editors and PowerShell often save UTF-8 with a byte-order mark.
    t = make_theme(count=8)
    path = t.dir / "theme.yaml"
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    from studio.theme import load_theme
    assert load_theme(t.dir, style_dir=t.dir.parent.parent / "style").name == "Test Cat"
