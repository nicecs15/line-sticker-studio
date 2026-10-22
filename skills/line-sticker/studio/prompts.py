"""Turn a theme into image prompts (for ChatGPT copy-paste or the OpenAI API)."""
from .theme import CLI


def sticker_prompt(theme, sticker, with_reference):
    if with_reference:
        intro = ("Create a LINE sticker of the SAME character as the attached reference image. "
                 "Keep the face, colors, outfit and art style identical.")
    else:
        intro = "Create a LINE sticker featuring this original character."
    lines = [intro, f"Character: {theme.character}", theme.style_lock]
    lines.append("Create a distinct pose and expression for this sticker. "
                 "Use the reference for character identity only; do not copy its pose. "
                 "Do not reuse another sticker image with a different caption.")
    if theme.style_notes:
        lines.append(theme.style_notes)
    if theme.lettering:
        lines.append("TEXT-FREE ARTWORK: draw NO text, letters, numbers, speech bubbles or signs anywhere; "
                     "the caption is typeset later by software. "
                     + ("Full-body portrait composition (about 3:4) that fills the frame top to bottom, "
                        if theme.export_type == "big" else
                        "Compact silhouette that fills the frame, square or slightly portrait, ")
                     + "with the face large and nothing cropped.")
    elif theme.export_type == "big":
        lines.append("BIG STICKER: portrait 3:5 composition, designed for 396 x 660 px. "
                     "Artwork silhouette must fill at least 80% of canvas height and nearly full width. "
                     "Stack large bold Thai text above a prominent character with minimal gaps. "
                     "Use short readable lines, intact diacritics and high contrast. "
                     "Do not center a square image on a tall empty canvas or stretch the artwork.")
    lines.append("")
    if sticker.pose:
        lines.append(f"Pose: {sticker.pose}")
    if sticker.props:
        lines.append(f"Props: {sticker.props}")
    if theme.lettering:
        if sticker.text:
            lines.append(f'Mood to act out (do NOT write it): "{" ".join(sticker.text.split())}"')
    elif sticker.text:
        breaks = ", ' / ' marks a line break" if "\n" in sticker.text.strip() else ""
        text = f'Text (exact spelling{breaks}): "{sticker.label}"'
        lines.append(f"{text}. Layout: {sticker.text_style}" if sticker.text_style else text)
    else:
        lines.append("No text on this sticker.")
    return "\n".join(lines).strip()


def _section(theme, sticker, mark, with_reference):
    return (f"### {mark} {sticker.n:02d} · `{sticker.label or '(no text)'}`\n"
            f"```text\n{sticker_prompt(theme, sticker, with_reference)}\n```\n")


def render_prompts_md(theme):
    has_ref = theme.reference.exists()
    done, missing = theme.done(), theme.missing()
    undrafted = set(theme.undrafted())

    out = [f"# {theme.name}: prompts", "",
           "> ไฟล์นี้สร้างอัตโนมัติจาก `theme.yaml` ถ้าจะแก้ ให้แก้ที่ theme.yaml "
           f"แล้วรัน `{CLI} prompts {theme.id}` ใหม่", "",
           f"- ความคืบหน้า: **{len(done)}/{theme.count}** ภาพ",
           f"- reference.png: {'✅ มีแล้ว' if has_ref else '⬜ ยังไม่มี'}"]
    if missing:
        out.append(f"- ยังขาด: {', '.join(f'{n:02d}' for n in missing)}")
    if undrafted:
        out.append(f"- ⚠️ ยังไม่ได้ร่างคำพูด: {', '.join(f'{n:02d}' for n in sorted(undrafted))} "
                   "(ให้ AI agent ร่างเพิ่มใน theme.yaml)")

    out += ["", "## วิธีใช้กับ ChatGPT", ""]
    if has_ref:
        out.append(f"1. เปิดแชตใหม่ใน ChatGPT แล้ว **แนบ `themes/{theme.id}/reference.png`** เป็นภาพอ้างอิง")
    else:
        out.append("1. ยังไม่มีภาพอ้างอิง: ทำภาพแรกก่อน **โดยไม่ต้องแนบภาพ** เมื่อได้ภาพที่ชอบแล้ว "
                   f"import เข้ามา แล้วรัน `{CLI} reference {theme.id} <เลขภาพ>` "
                   "จากนั้นรันคำสั่ง prompts ใหม่ (prompt จะเปลี่ยนเป็นแบบแนบภาพอ้างอิง)")
    out += [
        "2. ก๊อป prompt ไปวาง **ทีละภาพ ตามลำดับเลข** (ถ้ามีหลายภาพเกิน 1 แชต ให้แนบ reference ใหม่ทุกครั้งที่เปิดแชตใหม่)",
        ("3. ถ้ามีตัวอักษรโผล่มาในภาพ สั่งแก้ว่า: `remove all text from the image` " if theme.lettering else
         "3. ถ้าตัวอักษรไทยเพี้ยน สั่งแก้ซ้ำว่า: `แก้ตัวอักษรให้สะกดตรงตามนี้เป๊ะ: \"...\"` ")
        + "ถ้าพื้นหลังไม่ใส สั่ง: `make the background fully transparent`",
        f"4. ดาวน์โหลด PNG ไปไว้ที่ `themes/{theme.id}/inbox/` แล้วรัน `{CLI} import {theme.id}` "
        "(ไฟล์จะถูกจับเลขตามลำดับเวลาดาวน์โหลด เข้าช่องที่ยังว่าง; ระบุเองได้ด้วย `--as NN ไฟล์.png`)",
        (f"5. ภาพที่ได้ต้องไม่มีตัวอักษร (ระบบพิมพ์คำไทยด้วยฟอนต์ให้เอง) ดูตัวอย่างได้ด้วย `{CLI} compose {theme.id}` "
         f"ครบแล้วรัน `{CLI} build {theme.id}` แล้วอัปโหลด zip ใน `dist/` ขึ้น LINE Creators Market"
         if theme.lettering else
         f"5. ครบแล้วรัน `{CLI} build {theme.id}` แล้วอัปโหลด zip ใน `dist/` ขึ้น LINE Creators Market"),
        "",
    ]

    todo = [s for s in theme.stickers if s.n in missing]
    finished = [s for s in theme.stickers if s.n not in missing]
    if todo:
        out += ["## ⬜ ที่ยังต้องทำ", ""] + [_section(theme, s, "⬜", has_ref) for s in todo]
    if finished:
        out += ["## ✅ ทำแล้ว (เผื่ออยากทำใหม่)", ""] + [_section(theme, s, "✅", has_ref) for s in finished]

    out += ["## สรุปคำทั้งชุด", "", "| # | คำ | สถานะ |", "|---|---|---|"]
    for n in range(1, theme.count + 1):
        s = theme.sticker(n)
        status = "✅" if n not in missing else "⬜"
        out.append(f"| {n:02d} | {s.label if s else '(ยังไม่ได้ร่าง)'} | {status} |")
    return "\n".join(out) + "\n"


def write_prompts(theme):
    path = theme.dir / "prompts.md"
    path.write_text(render_prompts_md(theme), encoding="utf-8")
    return path
