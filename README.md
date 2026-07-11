# D&D Item Card Generator

Generate print-ready **item cards** for Dungeons & Dragons in the style of the
official Gale Force Nine cards, as **A4 landscape sheets** ready to fold into
double-sided cards.

This is a fork focused solely on item cards. Compared to the original
[DnD-Card-Generator](https://github.com/ep1cman/DnD-Card-Generator) it:

- supports **item cards only** (monster cards, the EncounterPlus converter and the
  `pdfjam`-based splitter have been removed);
- renders cards as a **coloured border + white body** (no D&D logo, no parchment
  background);
- gives every card a **consistent border** with a thick bottom band carrying the
  item name (front) and type (back);
- lets a card's **`color`** drive the border *and* the subtitle band;
- **auto-grows** an overflowing card from the small template to a double-width
  large template;
- tiles cards **natively** onto A4 landscape sheets (4 small cards or 2 large
  cards per page) — no TeX/`pdfjam` dependency;
- ships as a **`cardgen`** Python library plus (see Phase B) a local web GUI in a
  lightweight Docker container.

## The `cardgen` library

```python
from cardgen import render_item_cards, RenderOptions

entries = [
    {
        "title": "Vicious Battleaxe",
        "subtitle": "Weapon (battleaxe), rare",
        "category": "Weapon",
        "subcategory": "Battleaxe",
        "color": "#4a4a4a",
        "description": [
            "This axe is a magic weapon. When you roll a 20 on an attack roll "
            "made with this weapon, the target takes an extra 7 (2d6) damage.",
        ],
    },
]

pdf_bytes = render_item_cards(entries, RenderOptions(fonts="free"))
open("cards.pdf", "wb").write(pdf_bytes)
```

`render_item_cards(entries, options)` returns the PDF as bytes. Titles of any
cards that do not fit even the large template are collected in `options.errors`.

## Command line

```
python -m cardgen.cli input.yaml -o cards.pdf [-f free|accurate] [-b BLEED_MM]
```

Example YAML files are in the `example/` directory.

## Card fields (YAML / entry dict)

- **title** — item name; shown centred in the front bottom band and as the heading on the back.
- **subtitle** — text in the coloured band on the back (its background follows `color`).
- **category** / **subcategory** — the item type, shown centred in the back bottom band as `Category (Subcategory)`.
- **description** — a string, or a list whose entries are either strings or single-key `{name: text}` dicts (the value may be omitted).
- **color** — a colour name (`red`), hex code (`#4a4a4a`) or anything ReportLab accepts; drives the border and subtitle band.
- **image_path** — optional path to artwork; falls back to `assets/placeholder_item.png`.
- **artist** — optional; currently unused by the renderer.

## Fonts

Free fonts that resemble the official ones ship in `assets/fonts`. To use the
exact official fonts, place the Modesto TTFs in `assets/fonts` and pass
`-f accurate` (they are not distributed with this repo).

## Development

```
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python tests/test_render.py     # render tests (no pytest required)
```

## Acknowledgements

- Fonts: [Scaly Sans](https://github.com/jonathonf/solbera-dnd-fonts) by Solbera,
  Ryrok and jonathonf; [Universal Sans](https://www.dafont.com/universal-serif.font)
  by Khiam Mincey.
- All Wizards of the Coast content under the Open Gaming License Version 1.0a.
