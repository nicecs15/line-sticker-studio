"""Duplicate checks independent of PNG metadata and Thai text layout."""
import hashlib
import unicodedata

from PIL import Image

from .images import clean


def text_key(text):
    # Keep Thai letters/diacritics, but ignore layout, punctuation and invisible spacing.
    return "".join(c for c in unicodedata.normalize("NFKC", text).casefold()
                   if unicodedata.category(c)[0] in "LMN")


def repeated_texts(stickers):
    seen, issues = {}, []
    for sticker in stickers:
        key = text_key(sticker.text)
        if not key:  # Multiple intentionally text-free stickers are allowed.
            continue
        if key in seen:
            issues.append(f"คำพูดซ้ำ {seen[key]:02d} / {sticker.n:02d}: {sticker.text!r}")
        else:
            seen[key] = sticker.n
    return issues


def repeated_poses(stickers):
    seen, issues = {}, []
    for sticker in stickers:
        key = text_key(sticker.pose)
        if key and key in seen:
            issues.append(f"ท่าทางซ้ำ {seen[key]:02d} / {sticker.n:02d}: {sticker.pose!r}")
        elif key:
            seen[key] = sticker.n
    return issues


def image_key(path):
    with Image.open(path) as original:
        im = clean(original)
    bbox = im.getchannel("A").getbbox()
    if bbox is None:
        return None
    im = im.crop(bbox)
    return hashlib.sha256(str(im.size).encode() + im.tobytes()).hexdigest()


def image_duplicates(theme):
    issues = []
    # Check text-free artwork too, so changing the caption cannot hide reused art.
    for folder in (theme.source_dir, theme.dir / "art"):
        seen = {}
        for path in sorted(folder.glob("[0-9][0-9].png")):
            key = image_key(path)
            if key is None:
                continue
            if key in seen:
                issues.append(f"ภาพซ้ำ {folder.name}/{seen[key]} / {folder.name}/{path.name}")
            else:
                seen[key] = path.name
    return issues


def cross_theme_duplicates(theme):
    """Report reuse against sibling themes without loading their style dependencies."""
    import yaml

    texts = {text_key(s.text): s.n for s in theme.stickers if text_key(s.text)}
    images = {}
    for folder in (theme.source_dir, theme.dir / "art"):
        for path in sorted(folder.glob("[0-9][0-9].png")):
            key = image_key(path)
            if key:
                images[key] = f"{folder.name}/{path.name}"
    issues = []
    for other in sorted(theme.dir.parent.iterdir()):
        if not other.is_dir() or other.resolve() == theme.dir.resolve():
            continue
        manifest = other / "theme.yaml"
        if not manifest.exists():
            continue
        try:
            data = yaml.safe_load(manifest.read_text(encoding="utf-8-sig")) or {}
            for sticker in data.get("stickers", []):
                key = text_key(str(sticker.get("text", "")))
                if key and key in texts:
                    issues.append(f"คำพูดซ้ำข้ามชุด {theme.id}/{texts[key]:02d} / "
                                  f"{other.name}/{sticker['n']}: {sticker['text']!r}")
        except (yaml.YAMLError, KeyError, TypeError, AttributeError) as e:
            from .theme import ThemeError
            raise ThemeError(f"Cannot check duplicates against {manifest}: {e}") from e
        for folder in (other / "source", other / "art"):
            for path in sorted(folder.glob("[0-9][0-9].png")):
                key = image_key(path)
                if key and key in images:
                    issues.append(f"ภาพซ้ำข้ามชุด {theme.id}/{images[key]} / "
                                  f"{other.name}/{folder.name}/{path.name}")
    return issues


def check_duplicates(theme, *, include_other_themes=False):
    from .theme import ThemeError

    issues = repeated_texts(theme.stickers) + repeated_poses(theme.stickers) + image_duplicates(theme)
    if include_other_themes:
        issues += cross_theme_duplicates(theme)
    if issues:
        raise ThemeError("Duplicate stickers detected:\n" + "\n".join(issues))
