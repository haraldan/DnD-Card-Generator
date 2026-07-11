import os

from copy import copy

from reportlab.lib.units import mm
from reportlab.platypus import Frame, Paragraph
from reportlab.platypus.flowables import Spacer, Image

from .flowables import Border, TemplateTooSmall, get_image_size
from .fonts import FreeFonts


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
        artist,
        image_path,
        border_color="red",
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
        self.artist = artist
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
    def _draw_front_frame(self, canvas, width, height):
        front_frame = Frame(
            self.border_front[Border.LEFT],
            self.border_front[Border.BOTTOM],
            width - self.border_front[Border.LEFT] - self.border_front[Border.RIGHT],
            height - self.border_front[Border.TOP] - self.border_front[Border.BOTTOM],
            leftPadding=self.TEXT_MARGIN,
            bottomPadding=self.TEXT_MARGIN,
            rightPadding=self.TEXT_MARGIN,
            topPadding=self.TEXT_MARGIN,
        )

        available_width = front_frame.width - 2 * self.TEXT_MARGIN
        available_height = front_frame.height - 2 * self.TEXT_MARGIN

        image_width, image_height = get_image_size(
            self.front_image_path, available_width, available_height
        )

        elements = []
        space = available_height - image_height
        if space > 0:
            elements.append(Spacer(available_width, space / 2))
        elements.append(Image(self.front_image_path, image_width, image_height))
        if space > 0:
            elements.append(Spacer(available_width, space / 2))

        front_frame.addFromList(elements, canvas)

    def _draw_frames(self, canvas, split=False):
        frames = iter(self.frames)
        current_frame = next(frames)

        while len(self.elements) > 0:
            element = self.elements.pop(0)

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
        # Artwork fills the content area above the bottom band
        self._draw_front_frame(canvas, self.width, self.height)
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
        border_front=(2.5 * mm, 2.5 * mm, 7.5 * mm, 2.5 * mm),
        border_back=(2.5 * mm, 2.5 * mm, 7.5 * mm, 2.5 * mm),
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
        border_back=(3.5 * mm, 3.5 * mm, 7.5 * mm, 3.5 * mm),
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
    def __init__(
        self,
        title,
        subtitle,
        artist,
        image_path,
        category,
        subcategory,
        description,
        **kwargs,
    ):
        super().__init__(title, subtitle, artist, image_path, **kwargs)
        self.category = category
        self.subcategory = subcategory
        self.description = description

    def _band_baseline(self, section):
        """Vertical baseline that centres `section` font in the bottom band."""
        font_mm = self.fonts.styles[section][1] * self.fonts.FONT_SCALE
        return self.bleed + (self.BOTTOM_BAND - font_mm) / 2

    def _draw_front_label(self, canvas):
        if not self.title:
            return
        canvas.saveState()
        canvas.setFillColor("white")
        scale = min(1.0, 20 / len(self.title))
        self.fonts.set_font(canvas, "title", custom_scale=scale)
        font_mm = self.fonts.styles["title"][1] * self.fonts.FONT_SCALE * scale
        baseline = self.bleed + (self.BOTTOM_BAND - font_mm) / 2
        canvas.drawCentredString(self.width / 2, baseline, self.title.upper())
        canvas.restoreState()

    def _draw_back(self, canvas):
        super()._draw_back(canvas)

        canvas.saveState()
        canvas.setFillColor("white")
        self.fonts.set_font(canvas, "category")
        text = self.category or ""
        if self.subcategory:
            text += " ({})".format(self.subcategory)
        canvas.drawCentredString(self.width * 1.5, self._band_baseline("category"), text)
        canvas.restoreState()

    def fill_frames(self, canvas):
        # Title (heading on the back face)
        self.elements.append(self._get_title_paragraph())

        # Subtitle band — colour follows the card's border colour
        subtitle_style = copy(self.fonts.paragraph_styles["subtitle"])
        subtitle_style.backColor = self.border_color
        self.elements.append(Paragraph(self.subtitle, subtitle_style))

        # Space before the body text
        self.elements.append(Spacer(1 * mm, 1 * mm))

        if type(self.description) == str:
            self.elements.append(
                Paragraph(self.description, self.fonts.paragraph_styles["text"])
            )
            return
        if type(self.description) != list:
            raise ValueError(
                f"Item `{self.title}` description should be a `str` or `list`"
            )

        for entry in self.description:
            if type(entry) == str:
                self.elements.append(
                    Paragraph(entry, self.fonts.paragraph_styles["text"])
                )
            if type(entry) == dict:
                for title, description in entry.items():
                    text = f"<i><b>{title}.</b></i>"
                    if description is not None:
                        text += f" {description}"

                    self.elements.append(
                        Paragraph(text, self.fonts.paragraph_styles["text"])
                    )

    def _get_title_paragraph(self):
        return Paragraph(self.title, self.fonts.paragraph_styles["title"])


class ItemCardSmall(SmallCard, ItemCardLayout):
    pass


class ItemCardLarge(LargeCard, ItemCardLayout):
    pass
