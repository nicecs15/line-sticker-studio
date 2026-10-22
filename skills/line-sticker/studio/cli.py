"""Command line: python sticker.py <command> ..."""
import argparse
import shutil
import sys

from . import build as build_mod
from . import generate as generate_mod
from .doctor import doctor
from .importer import import_images
from .prompts import write_prompts
from .scaffold import new_theme
from .theme import CLI, ThemeError, load_theme, resolve, theme_dirs
from .duplicates import check_duplicates


def cmd_list(args):
    dirs = theme_dirs()
    if not dirs:
        print("No themes yet. Ask your AI agent (Codex / Claude Code) to make a sticker set, "
              f"or run: {CLI} new <id>")
        return
    for d in dirs:
        try:
            t = load_theme(d)
        except ThemeError as e:
            print(f"  {d.name:<24} ERROR {e}")
            continue
        ref = "ref" if t.reference.exists() else "no-ref"
        mode = "font" if t.lettering else "ai-text"
        zipped = "zip" if (t.dist_dir / f"{t.id}-line.zip").exists() else ""
        print(f"  {t.id:<24} {len(t.done()):>2}/{t.count:<2} {t.export_type:<7} {mode:<7} {ref:<6} {zipped:<3} {t.name}")


def cmd_prompts(args):
    t = load_theme(resolve(args.theme))
    check_duplicates(t)
    path = write_prompts(t)
    print(f"Wrote {path} ({len(t.missing())} still to make)")


def cmd_import(args):
    t = load_theme(resolve(args.theme))
    r = import_images(t, as_number=args.as_number, files=args.files or None, keep_bg=args.keep_bg)
    if not r.imported:
        print(f"Nothing to import. Put images in {t.inbox_dir}")
        return
    for name, n in r.imported:
        print(f"  {name} -> {t.raw_path(n).parent.name}/{n:02d}.png")
    for w in r.warnings:
        print(f"  WARNING {w}")
    if r.leftover:
        print(f"  No free slot for: {', '.join(r.leftover)} (use --as NN to replace one)")
    write_prompts(t)
    print(f"Progress {len(t.done())}/{t.count}; prompts.md updated")


def cmd_reference(args):
    t = load_theme(resolve(args.theme))
    src = t.raw_path(args.number)
    if not src.exists():
        raise ThemeError(f"{src} does not exist")
    shutil.copyfile(src, t.reference)
    write_prompts(t)
    print(f"reference.png <- {src.name}; prompts.md updated")


def cmd_generate(args):
    t = load_theme(resolve(args.theme))
    check_duplicates(t)
    nums = generate_mod.parse_range(args.only, t.count) if args.only else None
    done, failed = generate_mod.generate(t, nums, via=args.via, model=args.model, quality=args.quality,
                                         force=args.force, dry_run=args.dry_run)
    if not args.dry_run:
        write_prompts(t)
        print(f"Generated {len(done)}; failed {failed or 'none'}; progress {len(t.done())}/{t.count}")


def cmd_new(args):
    path = new_theme(args.theme, name=args.name, count=args.count,
                     export_type="regular" if args.regular else "big")
    print(f"Created {path}")
    print(f"Next: fill in character + stickers, then {CLI} prompts {args.theme}")


def cmd_compose(args):
    from .compose import compose
    t = load_theme(resolve(args.theme))
    nums = generate_mod.parse_range(args.only, t.count) if args.only else None
    done = compose(t, nums)
    print(f"Composed {len(done)} sticker(s) into {t.source_dir}")


def cmd_doctor(args):
    if not doctor():
        sys.exit(1)


def cmd_build(args):
    t = load_theme(resolve(args.theme))
    r = build_mod.build(t, include_other_themes=args.all_themes)
    print(f"Zip: {r.zip_path} ({r.zip_path.stat().st_size / 1024:.0f} KB, {r.count} stickers)")
    print(f"Preview: {r.preview_path}")
    if t.line is not None:
        print(f"LINE info: {t.dist_dir / 'line_info.txt'}")
    for note in r.notes:
        print(f"  NOTE {note}")


def cmd_check(args):
    t = load_theme(resolve(args.theme))
    check_duplicates(t, include_other_themes=args.all_themes)
    print(f"No duplicate captions or identical images: {t.id}")


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    p = argparse.ArgumentParser(prog="sticker.py", description="LINE sticker studio")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="check Python packages, fonts and Codex login").set_defaults(fn=cmd_doctor)
    sub.add_parser("list", help="all themes and progress").set_defaults(fn=cmd_list)

    s = sub.add_parser("new", help="create themes/<theme>/theme.yaml from a template")
    s.add_argument("theme", help="id: lowercase english with dashes, e.g. cat-accountant")
    s.add_argument("--name", help="display name (default: the id)")
    s.add_argument("--count", type=int, default=16, help="8/16/24/32/40 (default 16)")
    s.add_argument("--regular", action="store_true", help="regular 370x320 stickers instead of Big Stickers")
    s.set_defaults(fn=cmd_new)

    s = sub.add_parser("prompts", help="write themes/<theme>/prompts.md")
    s.add_argument("theme")
    s.set_defaults(fn=cmd_prompts)

    s = sub.add_parser("import", help="inbox/ images -> source/NN.png")
    s.add_argument("theme")
    s.add_argument("files", nargs="*", help="specific files (default: everything in inbox/)")
    s.add_argument("--as", dest="as_number", type=int, help="put one file at this number (replaces)")
    s.add_argument("--keep-bg", action="store_true", help="do not auto-remove white/checkered backgrounds")
    s.set_defaults(fn=cmd_import)

    s = sub.add_parser("reference", help="use source/NN.png as reference.png")
    s.add_argument("theme")
    s.add_argument("number", type=int)
    s.set_defaults(fn=cmd_reference)

    s = sub.add_parser("generate", help="make missing images automatically (Codex CLI or OpenAI API)")
    s.add_argument("theme")
    s.add_argument("--via", default="codex", choices=generate_mod.BACKENDS,
                   help="codex = Codex CLI on your ChatGPT plan (default); openai = paid Images API")
    s.add_argument("--only", help="e.g. 11-20,25")
    s.add_argument("--model", default=generate_mod.DEFAULT_MODEL, help="openai only")
    s.add_argument("--quality", default="high", choices=["low", "medium", "high"], help="openai only")
    s.add_argument("--force", action="store_true", help="regenerate even if the image exists")
    s.add_argument("--dry-run", action="store_true", help="print prompts only, generate nothing")
    s.set_defaults(fn=cmd_generate)

    s = sub.add_parser("compose", help="type captions onto art/NN.png -> source/NN.png (lettering themes)")
    s.add_argument("theme")
    s.add_argument("--only", help="e.g. 1-4,7")
    s.set_defaults(fn=cmd_compose)

    s = sub.add_parser("build", help="make dist/line_upload, zip and preview")
    s.add_argument("theme")
    scope = s.add_mutually_exclusive_group()
    scope.add_argument("--all-themes", dest="all_themes", action="store_true", help="also compare every other theme")
    scope.add_argument("--within-set", dest="all_themes", action="store_false", help="check this set only (default)")
    s.set_defaults(all_themes=False)
    s.set_defaults(fn=cmd_build)

    s = sub.add_parser("check", help="reject duplicate captions and identical images")
    s.add_argument("theme")
    scope = s.add_mutually_exclusive_group()
    scope.add_argument("--all-themes", dest="all_themes", action="store_true", help="also compare every other theme")
    scope.add_argument("--within-set", dest="all_themes", action="store_false", help="check this set only (default)")
    s.set_defaults(all_themes=False)
    s.set_defaults(fn=cmd_check)

    args = p.parse_args(argv)
    try:
        args.fn(args)
    except ThemeError as e:
        sys.exit(f"ERROR: {e}")
