import os

from copy import copy

from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Frame, Paragraph
from reportlab.platypus.flowables import Spacer

from .flowables import Border, LineDivider, TemplateTooSmall
from .fonts import FreeFonts
from .markdown_render import parse_markdown

# Default frame/subtitle colour: a muted slate blue. Pleasant on screen and a
# distinct mid-tone when printed in black and white.
DEFAULT_COLOR = "#3a5a78"

# Default body-text / subtitle size, in points.
DEFAULT_FONT_SIZE = 8.0


class CardLayout:
    CARD_CORNER_DIAMETER = 3 * mm
    BACKGROUND_CORNER_DIAMETER = 2 * mm
    STANDARD_BORDER = 2.5 * mm
    STANDARD_MARGIN = 1.0 * mm
    TEXT_MARGIN = 2 * mm
    BASE_WIDTH = 63 * mm
    BASE_HEIGHT = 89 * mm
    # Height of the coloured bottom band that carries the card's label text.
    BOTTOM_BAND = 7.5 * mm

    def __init__(
        self,
        title,
        subtitle,
        image_path,
        border_color=DEFAULT_COLOR,
        border_front=(0, 0, 0, 0),  # uninitialized
        border_back=(0, 0, 0, 0),  # uninitialized
        width=0,  # uninitialized
        height=0,  # uninitialized
        bleed=0,  # uninitialized
        fonts=None,
    ):
        self.frames = []
        self.title = title
        self.subtitle = subtitle
        self.fonts = fonts if fonts is not None else FreeFonts()
        self.border_color = border_color
        self.border_front = tuple([v + bleed for v in border_front])
        self.border_back = tuple([v + bleed for v in border_back])
        self.width = width + 2 * bleed
        self.height = height + 2 * bleed
        self.bleed = bleed
        self.front_image_path = os.path.abspath(image_path)
        self.elements = []

    # ------------------------------------------------------------------
    # Public entry point: draw this card at (x, y) on a shared canvas.
    # Unlike the old CLI path, this does NOT call setPageSize/showPage — the
    # caller composes several cards onto one A4 page via translate offsets.
    # ------------------------------------------------------------------
    def render_at(self, canvas, x, y, split=False):
        canvas.saveState()
        canvas.translate(x, y)
        self._draw_front(canvas)
        self._draw_back(canvas)
        self.fill_frames(canvas)
        self._draw_frames(canvas, split)
        self._draw_dividers(canvas)
        canvas.restoreState()

    # Hooks overridden by subclasses ----------------------------------
    def fill_frames(self, canvas):
        pass

    def _draw_front_label(self, canvas):
        pass

    def _draw_dividers(self, canvas):
        pass

    # ------------------------------------------------------------------
    def _body_rect(self, margins):
        """The white body rectangle (x, y, w, h) inside the given borders."""
        x = margins[Border.LEFT]
        y = margins[Border.BOTTOM]
        w = self.width - margins[Border.LEFT] - margins[Border.RIGHT]
        h = self.height - margins[Border.TOP] - margins[Border.BOTTOM]
        return x, y, w, h

    def _draw_front_image(self, canvas):
        """Draw the artwork so it *covers* the body area (cropping overflow),
        clipped to the rounded body rectangle so it fills the frame with no
        surrounding white space."""
        x, y, w, h = self._body_rect(self.border_front)
        iw, ih = ImageReader(self.front_image_path).getSize()
        scale = max(w / iw, h / ih)  # cover
        dw, dh = iw * scale, ih * scale
        dx = x + (w - dw) / 2
        dy = y + (h - dh) / 2

        canvas.saveState()
        clip = canvas.beginPath()
        clip.roundRect(x, y, w, h, self.BACKGROUND_CORNER_DIAMETER)
        canvas.clipPath(clip, stroke=0, fill=0)
        canvas.drawImage(
            self.front_image_path, dx, dy, width=dw, height=dh, mask="auto"
        )
        canvas.restoreState()

    def _draw_frames(self, canvas, split=False):
        frames = iter(self.frames)
        current_frame = next(frames)

        while len(self.elements) > 0:
            element = self.elements.pop(0)

            # Don't draw a divider with nothing after it (trailing rule).
            if isinstance(element, LineDivider) and len(self.elements) == 0:
                break

            result = current_frame.add(element, canvas)
            if result == 0:
                # Could not draw into current frame
                if split:
                    remaining = current_frame.split(element, canvas)
                    if len(remaining):
                        current_frame.add(remaining.pop(0), canvas)
                        self.elements = remaining + self.elements
                        continue

                # Put the element back and try the next frame
                self.elements.insert(0, element)
                try:
                    current_frame = next(frames)
                except StopIteration:
                    break

        if len(self.elements) > 0:
            raise TemplateTooSmall("Template too small")

    def _draw_front(self, canvas):
        canvas.saveState()
        # Coloured border
        self._draw_single_border(canvas, 0, self.width, self.height)
        # White card body (clipped rounded rect)
        self._draw_single_background(canvas, 0, self.border_front, self.width, self.height)
        # Artwork covers the body area above the bottom band
        self._draw_front_image(canvas)
        # Item name in the bottom band
        self._draw_front_label(canvas)
        canvas.restoreState()

    def _draw_back(self, canvas):
        # Coloured border
        self._draw_single_border(canvas, self.width, self.width, self.height)
        # White card body
        self._draw_single_background(
            canvas, self.width, self.border_back, self.width, self.height
        )

    def _draw_single_border(self, canvas, x, width, height):
        canvas.saveState()
        canvas.setFillColor(self.border_color)
        canvas.roundRect(
            x,
            0,
            width,
            height,
            max(self.CARD_CORNER_DIAMETER - self.bleed, 0.0 * mm),
            stroke=0,
            fill=1,
        )
        canvas.restoreState()

    def _draw_single_background(self, canvas, x, margins, width, height):
        canvas.saveState()
        canvas.setFillColor("white")
        clipping_mask = canvas.beginPath()
        clipping_mask.roundRect(
            x + margins[Border.LEFT],
            margins[Border.BOTTOM],
            width - margins[Border.RIGHT] - margins[Border.LEFT],
            height - margins[Border.TOP] - margins[Border.BOTTOM],
            self.BACKGROUND_CORNER_DIAMETER,
        )
        canvas.clipPath(clipping_mask, stroke=0, fill=1)
        canvas.restoreState()


class SmallCard(CardLayout):
    def __init__(
        self,
        width=CardLayout.BASE_WIDTH,
        height=CardLayout.BASE_HEIGHT,
        # Front keeps a thick bottom band for the item name; the text side has a
        # uniform thin border on all sides (no footer).
        border_front=(2.5 * mm, 2.5 * mm, 7.5 * mm, 2.5 * mm),
        border_back=(2.5 * mm, 2.5 * mm, 2.5 * mm, 2.5 * mm),
        **kwargs,
    ):
        super().__init__(
            width=width,
            height=height,
            border_front=border_front,
            border_back=border_back,
            **kwargs,
        )

        frame = Frame(
            self.width + self.border_back[Border.LEFT],
            self.border_back[Border.BOTTOM],
            self.width - self.border_back[Border.LEFT] - self.border_back[Border.RIGHT],
            self.height - self.border_back[Border.TOP] - self.border_back[Border.BOTTOM],
            leftPadding=self.TEXT_MARGIN,
            bottomPadding=self.TEXT_MARGIN,
            rightPadding=self.TEXT_MARGIN,
            topPadding=0,
        )
        self.frames.append(frame)


class LargeCard(CardLayout):
    def __init__(
        self,
        width=CardLayout.BASE_WIDTH * 2,
        height=CardLayout.BASE_HEIGHT,
        border_front=(3.5 * mm, 3.5 * mm, 7.5 * mm, 3.5 * mm),
        border_back=(3.5 * mm, 3.5 * mm, 3.5 * mm, 3.5 * mm),
        **kwargs,
    ):
        super().__init__(
            width=width,
            height=height,
            border_front=border_front,
            border_back=border_back,
            **kwargs,
        )

        column_width = (
            self.width / 2 - self.border_back[Border.LEFT] - self.STANDARD_BORDER / 2
        )
        column_height = (
            self.height - self.border_back[Border.TOP] - self.border_back[Border.BOTTOM]
        )

        left_frame = Frame(
            self.width + self.border_back[Border.LEFT],
            self.border_back[Border.BOTTOM],
            column_width,
            column_height,
            leftPadding=self.TEXT_MARGIN,
            bottomPadding=self.TEXT_MARGIN,
            rightPadding=self.TEXT_MARGIN,
            topPadding=0,
        )
        right_frame = Frame(
            self.width * 1.5 + self.STANDARD_BORDER / 2,
            self.border_back[Border.BOTTOM],
            column_width,
            column_height,
            leftPadding=self.TEXT_MARGIN,
            bottomPadding=self.TEXT_MARGIN,
            rightPadding=self.TEXT_MARGIN,
            topPadding=0,
        )
        self.frames.append(left_frame)
        self.frames.append(right_frame)

    def _draw_dividers(self, canvas):
        # Vertical divider between the two back-face text columns. It spans only
        # the content area, so it does not cut through the top border or the
        # centred label in the bottom band.
        band_top = self.border_back[Border.BOTTOM]
        content_top = self.height - self.border_back[Border.TOP]
        canvas.saveState()
        canvas.setFillColor(self.border_color)
        canvas.rect(
            self.width * 1.5 - self.STANDARD_BORDER / 2,
            band_top,
            self.STANDARD_BORDER,
            content_top - band_top,
            stroke=0,
            fill=1,
        )
        canvas.restoreState()


class ItemCardLayout(CardLayout):
    # Fraction of the font size occupied by cap height (for vertical centring).
    _CAP_HEIGHT_RATIO = 0.7

    def __init__(
        self,
        title,
        subtitle,
        image_path,
        description,
        font_size=None,
        **kwargs,
    ):
        super().__init__(title, subtitle, image_path, **kwargs)
        self.description = description
        # Body-text / subtitle size in points.
        self.font_size = float(font_size) if font_size else DEFAULT_FONT_SIZE

    def _band_baseline(self, font_mm):
        """Baseline that vertically centres text of the given cap size in the
        bottom band (accounts for cap height, not full font box)."""
        cap = font_mm * self._CAP_HEIGHT_RATIO
        return self.bleed + (self.BOTTOM_BAND - cap) / 2

    def _draw_front_label(self, canvas):
        # Item name, centred in the front bottom band. The title font is NOT
        # affected by font_size — only its length-based auto-shrink.
        if not self.title:
            return
        canvas.saveState()
        canvas.setFillColor("white")
        scale = min(1.0, 20 / len(self.title))
        self.fonts.set_font(canvas, "title", custom_scale=scale)
        font_mm = self.fonts.styles["title"][1] * self.fonts.FONT_SCALE * scale
        canvas.drawCentredString(
            self.width / 2, self._band_baseline(font_mm), self.title.upper()
        )
        canvas.restoreState()

    def _text_style(self):
        """Body-text paragraph style at the card's font size (points)."""
        style = copy(self.fonts.paragraph_styles["text"])
        style.fontSize = self.font_size
        style.leading = self.font_size * 1.2
        return style

    def _subtitle_style(self):
        """Subtitle style: same font size as the body text, on a coloured band
        that follows the card colour. The band grows with the text because it
        is the paragraph's backColor."""
        style = copy(self.fonts.paragraph_styles["subtitle"])
        style.backColor = self.border_color
        style.fontSize = self.font_size
        style.leading = self.font_size * 1.2
        return style

    def fill_frames(self, canvas):
        text_style = self._text_style()

        # Title heading on the back face (fixed size)
        self.elements.append(self._get_title_paragraph())

        # Subtitle band (scales with body text; colour follows the card colour)
        if self.subtitle:
            self.elements.append(Paragraph(self.subtitle, self._subtitle_style()))

        # Space before the body text
        self.elements.append(Spacer(1 * mm, 1 * mm))

        # Description is authored as Markdown.
        blocks = parse_markdown(self.description or "")
        for block in blocks:
            if block[0] == "divider":
                # Extend past the frame text padding so the rule reaches the
                # card body edges (the coloured border).
                self.elements.append(
                    LineDivider(fill_color=self.border_color, extend=self.TEXT_MARGIN)
                )
            else:
                self.elements.append(Paragraph(block[1], text_style))

    def _get_title_paragraph(self):
        return Paragraph(self.title, self.fonts.paragraph_styles["title"])


class ItemCardSmall(SmallCard, ItemCardLayout):
    pass


class ItemCardLarge(LargeCard, ItemCardLayout):
    pass
