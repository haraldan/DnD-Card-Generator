"""Translation between the browser's card representation and the native cardgen
entry schema that is rendered and stored as YAML.

Browser description rows are explicit so the UI can round-trip the empty-value
case:

    {"type": "text", "text": "..."}          <->  "..."
    {"type": "kv", "key": "K", "value": "V"} <->  {"K": "V"}   (value "" -> None)
"""
from typing import List

from pydantic import BaseModel, Field


class DescRow(BaseModel):
    type: str = "text"  # "text" | "kv"
    text: str = ""
    key: str = ""
    value: str = ""


class CardIn(BaseModel):
    title: str = ""
    subtitle: str = ""
    category: str = ""
    subcategory: str = ""
    color: str = "red"
    description: List[DescRow] = Field(default_factory=list)


def to_native(card: CardIn) -> dict:
    """Browser card -> native cardgen entry dict."""
    description = []
    for row in card.description:
        if row.type == "kv":
            key = row.key.strip()
            if not key:
                continue
            description.append({key: (row.value if row.value != "" else None)})
        else:
            if row.text != "":
                description.append(row.text)
    entry = {
        "title": card.title,
        "subtitle": card.subtitle,
        "category": card.category,
        "description": description,
    }
    if card.subcategory:
        entry["subcategory"] = card.subcategory
    if card.color:
        entry["color"] = card.color
    return entry


def to_browser(entry: dict) -> dict:
    """Native entry (from stored YAML) -> browser card dict."""
    rows = []
    desc = entry.get("description", [])
    if isinstance(desc, str):
        desc = [desc]
    for item in desc:
        if isinstance(item, dict):
            for k, v in item.items():
                rows.append({"type": "kv", "key": str(k), "value": "" if v is None else str(v)})
        else:
            rows.append({"type": "text", "text": str(item)})
    return {
        "id": entry.get("_id"),
        "title": entry.get("title", ""),
        "subtitle": entry.get("subtitle", ""),
        "category": entry.get("category", ""),
        "subcategory": entry.get("subcategory", "") or "",
        "color": entry.get("color", "red"),
        "description": rows,
        "has_image": bool(entry.get("image_path")),
    }
