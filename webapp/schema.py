"""Translation between the browser's card representation and the native cardgen
entry schema that is rendered and stored as YAML.

Browser description rows are explicit so the UI can round-trip the empty-value
case:

    {"type": "text", "text": "..."}          <->  "..."
    {"type": "kv", "key": "K", "value": "V"} <->  {"K": "V"}   (value "" -> None)
"""
from pydantic import BaseModel

from cardgen.layout import DEFAULT_COLOR


class CardIn(BaseModel):
    title: str = ""
    subtitle: str = ""
    color: str = DEFAULT_COLOR
    font_scale: float = 1.0
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
    if card.font_scale and card.font_scale != 1.0:
        entry["font_scale"] = card.font_scale
    return entry


def to_browser(entry: dict) -> dict:
    """Native entry (from stored YAML) -> browser card dict.

    The description is stored (and returned) as a Markdown string."""
    return {
        "id": entry.get("_id"),
        "title": entry.get("title", ""),
        "subtitle": entry.get("subtitle", ""),
        "color": entry.get("color", DEFAULT_COLOR),
        "font_scale": float(entry.get("font_scale", 1.0) or 1.0),
        "description": entry.get("description") or "",
        "has_image": bool(entry.get("image_path")),
    }
