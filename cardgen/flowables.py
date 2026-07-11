from enum import IntEnum

from reportlab.lib import utils
from reportlab.lib.units import mm
from reportlab.platypus.flowables import Flowable


class Border(IntEnum):
    LEFT = 0
    RIGHT = 1
    BOTTOM = 2
    TOP = 3


class TemplateTooSmall(Exception):
    """Raised when a card's content does not fit the chosen template size."""

    pass


class LineDivider(Flowable):
    """A thin horizontal rule that spans the full width of its frame, drawn in
    the card's border colour. Used to visually separate description sections."""

    def __init__(self, fill_color="black", line_height=0.35 * mm, spacing=1.2 * mm):
        self.fill_color = fill_color
        self.line_height = line_height
        self.spacing = spacing
        self.width = 0
        self.height = line_height + spacing

    def wrap(self, available_width, available_height):
        self.width = available_width
        return (self.width, self.height)

    def draw(self):
        canvas = self.canv
        canvas.setFillColor(self.fill_color)
        canvas.rect(0, self.spacing / 2, self.width, self.line_height, stroke=0, fill=1)


def get_image_size(path, available_width, available_height):
    """Return the (width, height) an image should be to fit the available space
    while preserving its aspect ratio."""
    img = utils.ImageReader(path)
    image_width, image_height = img.getSize()

    width_ratio = available_width / image_width
    height_ratio = available_height / image_height
    best_ratio = min(width_ratio, height_ratio)

    return (image_width * best_ratio, image_height * best_ratio)
