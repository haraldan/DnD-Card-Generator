"""Per-card YAML persistence in a (host-mountable) data directory.

Layout under CARDGEN_DATA_DIR (default /data):

    cards/<id>.yaml      one card per file (the same schema as example/*.yaml,
                         plus an internal `_id` key)
    images/<id>.<ext>    optional uploaded artwork for that card

Writes are atomic (temp file + os.replace) so a reader on the mounted volume
never sees a half-written file. Every public function validates that `card_id`
is a real UUID, so a request can never escape the data directory.
"""
import logging
import os
import pathlib
import tempfile
import uuid

import yaml

logger = logging.getLogger(__name__)

DATA_DIR = pathlib.Path(os.environ.get("CARDGEN_DATA_DIR", "/data"))
CARDS_DIR = DATA_DIR / "cards"
IMAGES_DIR = DATA_DIR / "images"
# Ordered list of card ids currently loaded for rendering (the "working list").
WORKING_FILE = DATA_DIR / "working.yaml"

_ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def init_storage():
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def _valid_id(card_id: str) -> str:
    # Raises ValueError if not a well-formed UUID; also normalises the form.
    return str(uuid.UUID(str(card_id)))


def _card_path(card_id: str) -> pathlib.Path:
    return CARDS_DIR / f"{_valid_id(card_id)}.yaml"


def _atomic_write(path: pathlib.Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def image_file(card_id: str):
    """Return the Path of this card's stored image, or None."""
    cid = _valid_id(card_id)
    for ext in _ALLOWED_IMAGE_EXTS:
        p = IMAGES_DIR / f"{cid}{ext}"
        if p.exists():
            return p
    return None


def save_image(card_id: str, ext: str, data: bytes) -> pathlib.Path:
    cid = _valid_id(card_id)
    ext = ext.lower()
    if ext not in _ALLOWED_IMAGE_EXTS:
        raise ValueError(f"unsupported image type: {ext}")
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    # Remove any previously stored image for this card (possibly a different ext).
    for existing in IMAGES_DIR.glob(f"{cid}.*"):
        existing.unlink()
    path = IMAGES_DIR / f"{cid}{ext}"
    fd, tmp = tempfile.mkstemp(dir=str(IMAGES_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return path


def save_card(card_id: str, entry: dict):
    """Persist a single card entry as YAML. `entry` uses the native cardgen
    schema (description is a list of str | single-key dict)."""
    cid = _valid_id(card_id)
    doc = {k: v for k, v in entry.items() if not k.startswith("_")}
    doc["_id"] = cid
    # Record the image as a path relative to cards/, so the stored YAML also
    # works with the CLI / hand-editing on the host mount.
    img = image_file(cid)
    if img is not None:
        doc["image_path"] = os.path.join("..", "images", img.name)
    else:
        doc.pop("image_path", None)
    _atomic_write(_card_path(cid), yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))


def load_card(card_id: str):
    """Return the stored entry dict (including `_id`), or None."""
    path = _card_path(card_id)
    if not path.exists():
        return None
    with open(path, "r") as f:
        return yaml.safe_load(f)


def delete_card(card_id: str):
    cid = _valid_id(card_id)
    path = _card_path(cid)
    if path.exists():
        path.unlink()
    for img in IMAGES_DIR.glob(f"{cid}.*"):
        img.unlink()
    # A deleted card can no longer be in the working list.
    remove_working(cid)


# --------------------------------------------------------------- working list
# The working list is an ordered list of {"id": <uuid>, "copies": <int>} — the
# cards currently loaded for rendering, and how many times each is rendered.
def load_working():
    """Return the ordered working list, dropping entries whose card file no
    longer exists and coalescing duplicates."""
    if not WORKING_FILE.exists():
        return []
    try:
        with open(WORKING_FILE, "r") as f:
            raw = yaml.safe_load(f) or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unreadable working list: %s", exc)
        return []
    result = []
    index = {}
    for item in raw:
        if isinstance(item, dict):
            rid, copies = item.get("id"), item.get("copies", 1)
        else:  # tolerate a bare id
            rid, copies = item, 1
        try:
            cid = _valid_id(rid)
        except ValueError:
            continue
        if not _card_path(cid).exists():
            continue
        copies = max(1, int(copies or 1))
        if cid in index:
            index[cid]["copies"] += copies
        else:
            entry = {"id": cid, "copies": copies}
            index[cid] = entry
            result.append(entry)
    return result


def _save_working(entries):
    _atomic_write(WORKING_FILE, yaml.safe_dump(entries, sort_keys=False))


def add_working(card_id: str):
    """Add the card to the working list, or increment its copies if present."""
    cid = _valid_id(card_id)
    entries = load_working()
    for entry in entries:
        if entry["id"] == cid:
            entry["copies"] += 1
            break
    else:
        entries.append({"id": cid, "copies": 1})
    _save_working(entries)


def set_working_copies(card_id: str, copies: int):
    """Set the copies for a card (adds it if missing; removes it if < 1)."""
    cid = _valid_id(card_id)
    copies = int(copies)
    entries = load_working()
    for entry in entries:
        if entry["id"] == cid:
            if copies >= 1:
                entry["copies"] = copies
            else:
                entries = [e for e in entries if e["id"] != cid]
            break
    else:
        if copies >= 1:
            entries.append({"id": cid, "copies": copies})
    _save_working(entries)


def remove_working(card_id: str):
    cid = _valid_id(card_id)
    entries = load_working()
    kept = [e for e in entries if e["id"] != cid]
    if len(kept) != len(entries):
        _save_working(kept)


def list_cards():
    """Return [{id, title}] for every well-formed card file, newest first.
    Malformed files are skipped with a warning rather than crashing."""
    init_storage()
    cards = []
    for path in CARDS_DIR.glob("*.yaml"):
        try:
            cid = _valid_id(path.stem)
        except ValueError:
            logger.warning("Ignoring card file with non-UUID name: %s", path.name)
            continue
        try:
            with open(path, "r") as f:
                doc = yaml.safe_load(f) or {}
            title = doc.get("title") or "(untitled)"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping unreadable card %s: %s", path.name, exc)
            continue
        cards.append({"id": cid, "title": title, "mtime": path.stat().st_mtime})
    cards.sort(key=lambda c: c["mtime"], reverse=True)
    for c in cards:
        c.pop("mtime", None)
    return cards


def used_colors():
    """Distinct card colours across all saved cards, most-used first."""
    counts = {}
    for path in CARDS_DIR.glob("*.yaml"):
        try:
            with open(path, "r") as f:
                doc = yaml.safe_load(f) or {}
        except Exception:  # noqa: BLE001
            continue
        color = doc.get("color")
        if color:
            counts[color] = counts.get(color, 0) + 1
    return [c for c, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def entry_for_render(card: dict) -> dict:
    """Given a stored/browser card entry, return a copy whose `image_path`
    points at the actual stored image (absolute) or is removed."""
    entry = {k: v for k, v in card.items()}
    cid = entry.get("_id")
    img = image_file(cid) if cid else None
    if img is not None:
        entry["image_path"] = str(img)
    else:
        entry.pop("image_path", None)
    return entry
