import base64
import io
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from conftest import sticker_image
import studio.generate as gen_mod
from studio.generate import generate, parse_range
from studio.theme import ThemeError


def _png_b64():
    buf = io.BytesIO()
    Image.new("RGBA", (64, 64), (10, 20, 30, 255)).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


class FakeImages:
    def __init__(self, fail_on=()):
        self.calls = []
        self.fail_on = fail_on

    def _resp(self, kind, kw):
        self.calls.append((kind, kw))
        if any(f'"คำ{n}"' in kw["prompt"] for n in self.fail_on):
            raise RuntimeError("boom")
        return SimpleNamespace(data=[SimpleNamespace(b64_json=_png_b64())])

    def generate(self, **kw):
        return self._resp("generate", kw)

    def edit(self, **kw):
        return self._resp("edit", kw)


def test_parse_range():
    assert parse_range("3-5, 8", 8) == [3, 4, 5, 8]
    with pytest.raises(ThemeError):
        parse_range("7-9", 8)


def test_first_image_becomes_reference_then_edits(make_theme):
    t = make_theme(count=8)
    images = FakeImages()
    done, failed = generate(t, [1, 2, 3], via="openai", client=SimpleNamespace(images=images),
                            log=lambda *_: None)

    assert done == [1, 2, 3] and failed == []
    assert [c[0] for c in images.calls] == ["generate", "edit", "edit"]
    assert all(c[1]["background"] == "transparent" for c in images.calls)
    assert t.reference.exists()


def test_skips_existing_and_undrafted_and_continues_after_failure(make_theme):
    t = make_theme(count=8, drafted=range(1, 7))
    sticker_image(t.reference)
    sticker_image(t.source_path(1))
    images = FakeImages(fail_on=[3])

    done, failed = generate(t, via="openai", client=SimpleNamespace(images=images), log=lambda *_: None)

    assert done == [2, 4, 5, 6]
    assert failed == [3]
    assert not t.source_path(7).exists()


def test_dry_run_makes_no_calls(make_theme):
    t = make_theme(count=8)
    images = FakeImages()
    out = []
    generate(t, via="openai", client=SimpleNamespace(images=images), dry_run=True, log=out.append)
    assert images.calls == []
    assert "8 image(s) would be generated with gpt-image" in out[-1]


# ---------- Codex backend (fake `codex exec`) ----------

class FakeCodex:
    """Stands in for subprocess.run: writes NN.png into the -C dir unless told to fail."""

    def __init__(self, busy_first=0, never=False, opaque=False):
        self.calls = []
        self.busy_left = busy_first
        self.never = never
        self.opaque = opaque

    def __call__(self, cmd, input, capture_output, timeout):
        self.calls.append(cmd)
        work = Path(cmd[cmd.index("-C") + 1])
        task = input.decode("utf-8")
        if self.busy_left:
            self.busy_left -= 1
            return SimpleNamespace(stdout=b"ERROR: Selected model is at capacity.", stderr=b"")
        if self.never:
            return SimpleNamespace(stdout=b"something else went wrong", stderr=b"")
        name = re.search(r"named (\d\d\.png)", task).group(1)
        sticker_image(work / name, transparent=not self.opaque)
        return SimpleNamespace(stdout=f"{work / name}".encode(), stderr=b"")


@pytest.fixture
def codex_on_path(monkeypatch):
    monkeypatch.setattr(gen_mod, "codex_executable", lambda: "codex")


def test_codex_generates_with_reference_and_thai_task(make_theme, codex_on_path):
    t = make_theme(count=8)
    sticker_image(t.reference)
    fake = FakeCodex()

    done, failed = generate(t, [2, 3], run=fake, log=lambda *_: None)

    assert done == [2, 3] and failed == []
    assert t.source_path(2).exists() and t.source_path(3).exists()
    cmd = fake.calls[0]
    assert cmd[:2] == ["codex", "exec"] and cmd[-1] == "-"
    assert Path(cmd[cmd.index("-i") + 1]).name == "reference.png"
    task = (t.inbox_dir / "_codex" / "02" / "task.txt").read_text(encoding="utf-8")
    assert 'Text (exact spelling): "คำ2"' in task and "named 02.png" in task


def test_codex_retries_when_busy_then_gives_up_on_other_errors(make_theme, codex_on_path):
    t = make_theme(count=8)
    sticker_image(t.reference)
    waits = []
    fake = FakeCodex(busy_first=2)
    done, _ = generate(t, [1], run=fake, wait=waits.append, log=lambda *_: None)
    assert done == [1] and len(fake.calls) == 3 and len(waits) == 2

    fake = FakeCodex(never=True)
    done, failed = generate(t, [2, 3], run=fake, wait=waits.append, log=lambda *_: None)
    assert done == [] and failed == [2, 3]
    assert len(fake.calls) == 2          # not "busy", so no retries


def test_codex_without_reference_bootstraps_it_and_cleans_background(make_theme, codex_on_path):
    t = make_theme(count=8)
    fake = FakeCodex(opaque=True)
    done, _ = generate(t, [1, 2], run=fake, log=lambda *_: None)
    assert done == [1, 2]
    assert "-i" not in fake.calls[0] and "-i" in fake.calls[1]
    assert t.reference.exists()
    assert Image.open(t.source_path(1)).getpixel((0, 0))[3] == 0
