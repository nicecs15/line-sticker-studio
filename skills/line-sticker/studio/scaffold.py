"""python sticker.py new <id>: start a theme folder from a commented template."""
import re

from .theme import THEMES_DIR, VALID_COUNTS, ThemeError

TEMPLATE = """\
name: {name}
description: ""
count: {count}               # 8/16/24/32/40
export_type: {export_type}   # big = Big Stickers 396x660 (shows larger in chat), regular = 370x320
style: clean-art      # style/clean-art.yaml: text-free chibi art; the program types the captions
main: 1               # sticker used for main.png / tab.png

# The program types every caption with a real Thai font, so spelling is always exact.
# Remove this block to let the image model draw the text itself (often misspells Thai).
lettering:
  font: Kanit-ExtraBold          # fonts/: Kanit-ExtraBold, Mitr-Bold, Itim-Regular, Sriracha-Regular
  position: top                  # caption above (top) or below (bottom) the character
  # colors: ["#FF5A5F", "#2E86DE"]   # caption colours, cycled per sticker
  # outline: "#2B2B35"

line:                 # LINE Creators Market sale page (build writes dist/line_info.txt)
  copyright: "Your Name"                   # <= 50 characters
  en: {{title: "TODO", description: "TODO"}}   # required; title <= 40, description <= 160
  th: {{title: "TODO", description: "TODO"}}

character: |
  TODO: describe the character in English so it can be redrawn identically every time:
  species/object, fur or skin colour, eyes, face marks, outfit and accessories with colours.

style_notes: |
  TODO: palette, e.g. warm orange, cream and teal accents.

stickers:
  # One entry per sticker, n = 1..count. Use \\n in text to choose the line break.
  - n: 1
    text: "สวัสดี\\nครับ"
    pose: "TODO: full-body greeting, waving one paw, big smile"
    props: ""
"""


def new_theme(theme_id, name=None, count=16, export_type="big", themes_dir=THEMES_DIR):
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", theme_id):
        raise ThemeError("theme id must be lowercase english letters/digits with dashes, e.g. cat-accountant")
    if count not in VALID_COUNTS:
        raise ThemeError(f"count must be one of {VALID_COUNTS}")
    folder = themes_dir / theme_id
    if folder.exists():
        raise ThemeError(f"{folder} already exists")
    folder.mkdir(parents=True)
    path = folder / "theme.yaml"
    path.write_text(TEMPLATE.format(name=name or theme_id, count=count, export_type=export_type),
                    encoding="utf-8")
    return path
