"""Translation between the browser's card representation and the native cardgen
entry schema that is rendered and stored as YAML.

Browser description rows are explicit so the UI can round-trip the empty-value
case:

    {"type": "text", "text": "..."}          <->  "..."
    {"type": "kv", "key": "K", "value": "V"} <->  {"K": "V"}   (value "" -> None)
"""
from pydantic import BaseModel

from cardgen.layout import DEFAULT_COLOR, DEFAULT_FONT_SIZE


class CardIn(BaseModel):
    title: str = ""
    subtitle: str = ""
    color: str = DEFAULT_COLOR
    font_size: float = DEFAULT_FONT_SIZE  # body/subtitle size in points
    # Description is authored as Markdown (the stored source of truth).
    description: str = ""


def to_native(card: CardIn) -> dict:
    """Browser card -> native cardgen entry dict."""
    entry = {
        "title": card.title,
        "subtitle": card.subtitle,
        "description": card.description,
    }
    if card.color:
        entry["color"] = card.color
    if card.font_size:
        entry["font_size"] = card.font_size
    return entry


def to_browser(entry: dict) -> dict:
    """Native entry (from stored YAML) -> browser card dict.

    The description is stored (and returned) as a Markdown string."""
    return {
        "id": entry.get("_id"),
        "title": entry.get("title", ""),
        "subtitle": entry.get("subtitle", ""),
        "color": entry.get("color", DEFAULT_COLOR),
        "font_size": float(entry.get("font_size") or DEFAULT_FONT_SIZE),
        "description": entry.get("description") or "",
        "has_image": bool(entry.get("image_path")),
    }
