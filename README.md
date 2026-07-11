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
- ships as a **`cardgen`** Python library plus a local **web GUI** in a
  lightweight Docker container.

## Web app (Docker)

The app serves a browser GUI on port 8000. Cards you create are autosaved as
YAML into `CARDGEN_DATA_DIR` (default `/data`), which you mount from the host,
and reloaded next time.

- Every edit autosaves to `<data>/cards/<id>.yaml`; uploaded artwork goes to
  `<data>/images/<id>.<ext>`. Both are plain files you can edit or back up on the
  host, and they survive container restarts.
- The **Library** panel lists saved cards; click one to reload it.
- Images are optional (a placeholder is used otherwise) and can be cropped to the
  card's aspect ratio in the browser before upload.

### Image publishing (GHCR)

A GitHub Actions workflow (`.github/workflows/docker-publish.yml`) builds and
pushes the image to the GitHub Container Registry on every push to `master`:

```
ghcr.io/<owner>/<repo>:latest
```

To build locally instead:

```
docker build -t ghcr.io/<owner>/<repo>:latest .
```

### Run it

The image does **not** bake in a user. Pick a user/group that owns your data
directory and make sure that directory is writable by it:

```
docker run -d -p 8000:8000 \
  --user 1000:1000 \
  -v /path/to/your/carddata:/data \
  ghcr.io/<owner>/<repo>:latest
```

Or with compose — see `docker-compose.yml`, which shows the `user:` and volume
you need to set. Then open <http://localhost:8000>.

To swap the placeholder artwork, also mount your own over
`/app/assets/D20.png` (read-only).

### Running the web app without Docker

```
.venv/bin/pip install -r requirements.txt
CARDGEN_DATA_DIR=./data .venv/bin/uvicorn webapp.main:app --port 8000
```

## The `cardgen` library

```python
from cardgen import render_item_cards, RenderOptions

entries = [
    {
        "title": "Vicious Battleaxe",
        "subtitle": "Weapon (battleaxe), rare",
        "color": "#3a5a78",
        "description": (
            "1d8 slashing\n\n"
            "---\n\n"
            "This axe is a magic weapon. When you roll a 20 on an attack roll "
            "made with this weapon, the target takes an extra 7 (2d6) damage."
        ),
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
- **subtitle** — text in the coloured band on the back (its background follows `color`); scales with `font_scale`.
- **description** — a **Markdown** string. Supported: a single newline is a line break and a blank line starts a new paragraph; `---` is a full-width horizontal rule in the frame colour; plus `*italic*`, `**bold**`, `***bold italic***`, and `[text](url)` links.
- **color** — a colour name, hex code (e.g. `#4a4a4a`) or anything ReportLab accepts; drives the border and subtitle band. Defaults to a muted slate blue that also reads well in black and white.
- **font_scale** — optional multiplier for the body-text and subtitle size (default `1.0`; e.g. `1.3` for larger text). Does not affect the title.
- **image_path** — optional path to artwork; the image is scaled to cover the frame. Falls back to `assets/D20.png`.

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
