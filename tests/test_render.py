"""End-to-end rendering tests for the cardgen library.

Run with: python -m pytest tests/ (pytest optional — this file also runs
standalone via `python tests/test_render.py`).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cardgen import render_item_cards, RenderOptions  # noqa: E402
from cardgen.render import PAGE_SIZE  # noqa: E402


def _page_count(pdf_bytes):
    # Count "/Type /Page" occurrences without a PDF dependency.
    return pdf_bytes.count(b"/Type /Page\n") + pdf_bytes.count(b"/Type/Page/")


SMALL = {
    "title": "Vicious Battleaxe",
    "subtitle": "Weapon (battleaxe), rare",
    "category": "Weapon",
    "subcategory": "Battleaxe",
    "color": "#4a4a4a",
    "description": [
        "This axe is a magic weapon. When you roll a 20 on an attack roll made "
        "with this weapon, the target takes an extra 7 (2d6) damage.",
    ],
}

# Exercises str, key:value, and empty-value dict (`Sticky:`) description rows.
BADGE = {
    "title": "Sticky Badge",
    "subtitle": "Wondrous item, rare",
    "category": "Wondrous item",
    "subcategory": "Badge",
    "description": [
        "A plain string row.",
        {"Proud": "You become unreasonably proud of your name."},
        {"Sticky": None},
    ],
}


def test_returns_pdf_bytes():
    pdf = render_item_cards([SMALL])
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")


def test_description_row_forms():
    # Should render without raising on all three description-row shapes.
    pdf = render_item_cards([BADGE])
    assert pdf.startswith(b"%PDF")


def test_page_size_is_a4_landscape():
    from reportlab.lib.units import mm

    w, h = PAGE_SIZE
    assert round(w / mm) == 297
    assert round(h / mm) == 210


def test_small_cards_four_per_page():
    # 5 small cards -> ceil(5/4) = 2 pages.
    pdf = render_item_cards([dict(SMALL, title=f"Card {i}") for i in range(5)])
    assert _page_count(pdf) == 2


def test_empty_input_yields_one_blank_page():
    pdf = render_item_cards([])
    assert pdf.startswith(b"%PDF")
    assert _page_count(pdf) == 1


def test_overflowing_card_reported_not_crashed():
    huge = dict(SMALL, title="Impossibly Long Tome")
    huge["description"] = [
        {f"Clause {i}": "word " * 400} for i in range(40)
    ]
    options = RenderOptions()
    pdf = render_item_cards([huge], options)
    assert pdf.startswith(b"%PDF")
    assert huge["title"] in options.errors


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"FAIL {name}: {exc}")
    sys.exit(1 if failures else 0)
