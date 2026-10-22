import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "line-sticker"


def test_skill_ships_the_repo_license():
    # Installing the skill copies only its folder, so it carries its own copy.
    assert (SKILL / "LICENSE.txt").read_text(encoding="utf-8") == (ROOT / "LICENSE").read_text(encoding="utf-8")


def test_skill_frontmatter_has_name_and_description():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    front = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert front and "name: line-sticker" in front.group(1) and "description:" in front.group(1)


def test_every_bundled_font_ships_its_license():
    fonts = SKILL / "fonts"
    for font in fonts.glob("*.ttf"):
        family = font.stem.split("-")[0]
        assert (fonts / f"OFL-{family}.txt").exists(), f"{font.name} needs fonts/OFL-{family}.txt"


def test_installed_skill_works_from_another_folder(tmp_path):
    """The skill folder alone, run from the user's work folder, keeps themes in that folder."""
    work = tmp_path / "my-stickers"
    work.mkdir()

    def run(*args):
        return subprocess.run([sys.executable, str(SKILL / "sticker.py"), *args], cwd=work,
                              capture_output=True, text=True, encoding="utf-8")

    r = run("new", "demo-cat", "--count", "8")
    assert r.returncode == 0, r.stderr
    assert (work / "themes" / "demo-cat" / "theme.yaml").exists()
    assert not (SKILL / "themes").exists()
    r = run("prompts", "demo-cat")
    assert r.returncode == 0, r.stderr
    prompts = (work / "themes" / "demo-cat" / "prompts.md").read_text(encoding="utf-8")
    assert str(SKILL / "sticker.py") in prompts   # hints show the full command for a skill install
