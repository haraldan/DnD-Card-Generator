from enum import IntEnum

from reportlab.lib import utils


class Border(IntEnum):
    LEFT = 0
    RIGHT = 1
    BOTTOM = 2
    TOP = 3


class TemplateTooSmall(Exception):
    """Raised when a card's content does not fit the chosen template size."""

    pass


def get_image_size(path, available_width, available_height):
    """Return the (width, height) an image should be to fit the available space
    while preserving its aspect ratio."""
    img = utils.ImageReader(path)
    image_width, image_height = img.getSize()

    width_ratio = available_width / image_width
    height_ratio = available_height / image_height
    best_ratio = min(width_ratio, height_ratio)

    return (image_width * best_ratio, image_height * best_ratio)
