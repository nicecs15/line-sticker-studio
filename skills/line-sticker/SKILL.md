---
name: line-sticker
description: Make a LINE sticker set end to end - design an original character and Thai captions, generate the images on the user's ChatGPT plan through Codex, and build the LINE Creators Market zip. Use for ทำสติกเกอร์ / สติกเกอร์ไลน์ / LINE sticker, for new sets, and for changing captions or redoing images in an existing set.
---

# LINE sticker set

All work runs through the CLI bundled in this skill folder. In this file, `ST` stands for
`python "<the folder containing this SKILL.md>/sticker.py"`, e.g. `ST doctor`.
Run it from the user's working folder: sticker sets live in `./themes/<id>/` there, never inside the skill.
Every command takes `--help`.

A set is the folder `themes/<id>/`; its `theme.yaml` is the single source of truth.
New sets use **font lettering** (`lettering:` in theme.yaml): the image model draws text-free art into
`art/NN.png`, and `build` types each caption with a real Thai font into `source/NN.png`.
Thai spelling is therefore always exact, and a caption edit is a rebuild, never a new image.

## Steps

### 1. Machine ready

Run `ST doctor`. Done when it prints `Ready to make stickers.`
Fix each `XX` line with the command printed under it; `pip install` needs network, so request approval to
run it outside the sandbox. Python itself and the Codex CLI are installed by the user (see the hints).
The `--` line about the Codex login is advisory: a sandboxed run cannot see the login, and `generate`
(which runs outside the sandbox) reports a real logout itself.
With no Codex CLI, the set can still be made through the ChatGPT branch in step 4.

### 2. Set drafted

1. Settle at most two open questions with the user, only those the request leaves open:
   who it is for (friends, team, customers), count (8/16/24/32/40, default 16),
   polite particle (ครับ / ค่ะ / none), Big Stickers (default) or regular.
2. `ST new <id> --count N` (`--regular` for 370x320). The id is lowercase English with dashes.
3. Fill every `TODO` in `themes/<id>/theme.yaml`:
   - `character`: an English character lock precise enough to redraw identically: species or object,
     colours of fur/skin/eyes, face marks, outfit and accessories with every colour named.
     The design is original and recognisable; it resembles no brand or existing character.
   - `line`: sale-page text. `en` is required; title ≤ 40, description ≤ 160, copyright ≤ 50 characters.
     Ask the user for the copyright name.
   - `stickers`: exactly `count` entries, n = 1..count, each with `text` and `pose` (`props` optional).
     - Sticker 1 is a full-body greeting with the whole character clearly visible; it becomes the reference.
     - About half the captions are everyday chat (สวัสดี, ขอบคุณ, ขอโทษ, รับทราบ, รอแป๊บ, สู้ๆ, ฝันดี),
       half are jokes and situations specific to the theme.
     - Captions are short: one or two lines of at most ~10 Thai characters each, line break written as `\n`
       inside a double-quoted string. Big Stickers read best with two lines.
     - Every caption and every pose is distinct; each pose is a different action and expression.
     - `pose` and `props` are English; `text` is exactly what appears on the sticker.
     - Quote any YAML value containing `:` or `"`.
4. Run `ST prompts <id>` and `ST check <id>`.

Done when both commands succeed and `prompts.md` lists no undrafted numbers.
Show the user the caption table from the end of `prompts.md` and get their go-ahead:
images spend their ChatGPT quota and about two minutes each.

For a quick demo instead, copy `examples/cat-accountant/` from this skill folder into `./themes/` and continue at step 3.

### 3. Reference character approved

`ST generate <id> --only 1`, then show the user `themes/<id>/reference.png`.
If they want a different look, delete `reference.png` and `art/01.png`, adjust `character`, and generate again.
Done when the user accepts the reference.

### 4. All images made

**Codex branch (default):** `ST generate <id>` makes every missing image, one `codex exec` per image;
run it in the background for a full set. Rerun the same command to retry failures; existing images are skipped.
`generate` needs network access: inside a Codex sandbox, request approval to run it outside the sandbox,
or hand the user the command to run in their own terminal. Logs: `themes/<id>/inbox/_codex/NN/run.log`.

**ChatGPT branch (no Codex CLI):** the user pastes each prompt from `prompts.md` into ChatGPT with
`reference.png` attached, saves each result into `themes/<id>/inbox/` (naming it `NN.png` pins it to that
number), then runs `ST import <id>`.

Done when `ST list` shows `count/count` for the set.

### 5. Set reviewed

`ST build <id>`, then open `themes/<id>/dist/preview.png` and inspect every sticker:
same character as the reference, a distinct pose each, no stray text drawn into the art, nothing cropped.
Redo an image with `ST generate <id> --only N --force`; change a caption by editing `theme.yaml` and rebuilding.

Done when build prints no `NOTE` lines and every sticker in the preview passes the inspection.

### 6. Delivered

Tell the user:
- `themes/<id>/dist/<id>-line.zip`: the upload for LINE Creators Market.
- `dist/line_info.txt`: title, description and copyright to paste into the sale page.
- `dist/upload_type.txt`: for Big Stickers, choose บิ๊กสติกเกอร์ when creating the item.
- LINE reviews every set; they check their current guidelines on AI-generated images before submitting.

## Reference

- Lettering options (`lettering:` in theme.yaml): `font` (any file stem in this skill's `fonts/`:
  Kanit-ExtraBold, Mitr-Bold, Itim-Regular, Sriracha-Regular), `position` (top / bottom),
  `colors` (cycled per sticker), `outline`; a sticker's own `color` overrides. Removing `lettering:` makes
  the image model draw the text itself, with `style: big-readable` or `default`.
- A Big Sticker build refuses art that ends up shorter than 524 px; the error names the fix
  (portrait art via `--force`, or a two-line caption).
- `check` and `build` reject repeated captions, poses and images within the set. `--all-themes` also compares
  against every other set in `./themes/`, for users who want captions unique across their whole catalogue.
- `ST generate <id> --via openai` uses the paid OpenAI Images API (`OPENAI_API_KEY`) instead of the ChatGPT plan.
- The environment variable `LINE_STICKER_THEMES` points the CLI at another sets folder.
