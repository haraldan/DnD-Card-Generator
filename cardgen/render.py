import io
import logging
from dataclasses import dataclass, field

from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFError
from reportlab.pdfgen import canvas as canvas_module

from .flowables import TemplateTooSmall
from .fonts import FreeFonts, AccurateFonts
from .images import resolve_image
from .layout import CardLayout, ItemCardSmall, ItemCardLarge, DEFAULT_COLOR

logger = logging.getLogger(__name__)

# A4 landscape
PAGE_SIZE = (297 * mm, 210 * mm)

# A single card renders its front + back side by side, so a "pair" is twice the
# card's own width. Small cards are 63mm wide (pair 126mm); large cards are
# 126mm wide (pair 252mm). Both are 89mm tall.
_SMALL_PAIR_W = CardLayout.BASE_WIDTH * 2  # 126mm
_LARGE_PAIR_W = CardLayout.BASE_WIDTH * 4  # 252mm
_PAIR_H = CardLayout.BASE_HEIGHT  # 89mm


def _grid_slots(pair_w, pair_h, cols, rows):
    """Bottom-left origins for a centred cols x rows grid on the A4 page."""
    page_w, page_h = PAGE_SIZE
    margin_x = (page_w - cols * pair_w) / 2
    margin_y = (page_h - rows * pair_h) / 2
    slots = []
    # Fill top row first, left to right, then downward.
    for row in range(rows):
        y = margin_y + (rows - 1 - row) * pair_h
        for col in range(cols):
            slots.append((margin_x + col * pair_w, y))
    return slots


# Small cards: 2x2 => 4 per page. Large cards: 1 column x 2 rows => 2 per page.
SMALL_SLOTS = _grid_slots(_SMALL_PAIR_W, _PAIR_H, cols=2, rows=2)
LARGE_SLOTS = _grid_slots(_LARGE_PAIR_W, _PAIR_H, cols=1, rows=2)

# Size escalation order: try small first, grow to large only if text overflows.
_SIZES = [ItemCardSmall, ItemCardLarge]


@dataclass
class RenderOptions:
    fonts: str = "free"  # "free" | "accurate"
    bleed_mm: float = 0.0
    # Titles of cards that could not be fit at any size are appended here.
    errors: list = field(default_factory=list)


def _build_fonts(options):
    if options.fonts == "accurate":
        try:
            return AccurateFonts()
        except TTFError as exc:
            raise RuntimeError(
                "Failed to load accurate fonts; are the Modesto TTFs present?"
            ) from exc
    return FreeFonts()


def _entry_to_kwargs(entry, options):
    # Drop internal (persistence) keys such as `_id`.
    clean = {k: v for k, v in entry.items() if not k.startswith("_")}
    return {
        "title": clean.get("title", ""),
        "subtitle": clean.get("subtitle", ""),
        "image_path": resolve_image(clean),
        "description": clean.get("description", ""),
        "border_color": clean.get("color") or DEFAULT_COLOR,
        "font_size": clean.get("font_size"),
        "bleed": options.bleed_mm * mm,
    }


def _probe_size(kwargs, fonts):
    """Return the first (size_class, split) that fits, drawing onto a throwaway
    canvas so a failed attempt never pollutes the real page."""
    for size_cls in _SIZES:
        for split in (False, True):
            scratch = canvas_module.Canvas(io.BytesIO(), pagesize=PAGE_SIZE)
            try:
                card = size_cls(fonts=fonts, **kwargs)
                card.render_at(scratch, 0, 0, split)
                return size_cls, split
            except TemplateTooSmall:
                continue
    return None


def _tile(canvas, items, slots, fonts, first_page):
    """Draw resolved items onto `canvas` in `slots`, paging as needed.
    Returns True if it emitted at least one page."""
    if not items:
        return False
    per_page = len(slots)
    for i, (kwargs, size_cls, split) in enumerate(items):
        if i % per_page == 0 and not (i == 0 and first_page):
            canvas.showPage()
        x, y = slots[i % per_page]
        card = size_cls(fonts=fonts, **kwargs)
        card.render_at(canvas, x, y, split)
    return True


def render_item_cards(entries, options=None) -> bytes:
    """Render a list of item-card entry dicts to a multi-page A4-landscape PDF
    (small cards 4-up, large cards 2-up) and return the PDF bytes.

    Cards that overflow even the large template are skipped and their titles
    collected in `options.errors`.
    """
    if options is None:
        options = RenderOptions()
    options.errors = []

    fonts = _build_fonts(options)

    smalls, larges = [], []
    for entry in entries:
        kwargs = _entry_to_kwargs(entry, options)
        probe = _probe_size(kwargs, fonts)
        if probe is None:
            options.errors.append(kwargs.get("title") or "<untitled>")
            logger.warning("Card %r does not fit any template size", kwargs.get("title"))
            continue
        size_cls, split = probe
        (smalls if size_cls is ItemCardSmall else larges).append(
            (kwargs, size_cls, split)
        )

    buf = io.BytesIO()
    c = canvas_module.Canvas(buf, pagesize=PAGE_SIZE)

    drew = _tile(c, smalls, SMALL_SLOTS, fonts, first_page=True)
    drew = _tile(c, larges, LARGE_SLOTS, fonts, first_page=not drew) or drew

    # Always emit at least one (blank) page so the PDF is valid.
    c.showPage()
    c.save()
    return buf.getvalue()
