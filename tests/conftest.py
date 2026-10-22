import os
import sys
from pathlib import Path

import pytest
import yaml
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "line-sticker"))

from studio.theme import load_theme  # noqa: E402


def sticker_image(path, transparent=True, size=(600, 500), color=(240, 120, 30, 255)):
    bg = (0, 0, 0, 0) if transparent else (255, 255, 255, 255)
    im = Image.new("RGBA", size, bg)
    ImageDraw.Draw(im).ellipse((100, 80, size[0] - 100, size[1] - 60), fill=color)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return path


def touch_mtime(path, t):
    os.utime(path, (t, t))


@pytest.fixture
def make_theme(tmp_path):
    style_dir = tmp_path / "style"
    style_dir.mkdir()
    (style_dir / "default.yaml").write_text("lock: |\n  STYLE-LOCK line\n", encoding="utf-8")

    def _make(count=8, drafted=None, **extra):
        drafted = range(1, count + 1) if drafted is None else drafted
        data = {
            "name": "Test Cat",
            "count": count,
            "character": "a tiny orange cat",
            "stickers": [{"n": n, "text": f"คำ{n}", "pose": f"pose {n}", "props": f"props {n}",
                          "text_style": f"style {n}"} for n in drafted],
            **extra,
        }
        tdir = tmp_path / "themes" / "test-cat"
        tdir.mkdir(parents=True, exist_ok=True)
        (tdir / "theme.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        return load_theme(tdir, style_dir=style_dir)

    return _make
