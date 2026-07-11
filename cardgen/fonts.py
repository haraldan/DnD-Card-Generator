from abc import ABC

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.lib.fonts import addMapping

from .paths import FONT_DIR


# TODO: Clean up the font object, it seems a bit crude
class Fonts(ABC):
    styles = {}
    # Scaling factor between the font size and its actual height in mm
    FONT_SCALE = None
    FONT_DIR = FONT_DIR

    def __init__(self):
        self._register_fonts()
        self.paragraph_styles = StyleSheet1()
        self.paragraph_styles.add(
            ParagraphStyle(
                name="title",
                fontName=self.styles["title"][0],
                fontSize=self.styles["title"][1] * self.FONT_SCALE,
                leading=self.styles["title"][1] * self.FONT_SCALE + 0.5 * mm,
                spaceAfter=0.5 * mm,
                alignment=TA_CENTER,
                textTransform="uppercase",
            )
        )
        self.paragraph_styles.add(
            ParagraphStyle(
                name="subtitle",
                fontName=self.styles["subtitle"][0],
                fontSize=self.styles["subtitle"][1] * self.FONT_SCALE,
                textColor=self.styles["subtitle"][2],
                # NOTE: backColor is intentionally NOT set here. The subtitle
                # band colour must follow each card's `color`, so it is applied
                # per-card at render time (see ItemCardLayout.fill_frames).
                leading=self.styles["subtitle"][1] * self.FONT_SCALE + 0.5 * mm,
                alignment=TA_CENTER,
                borderPadding=(0, 6),
            )
        )
        self.paragraph_styles.add(
            ParagraphStyle(
                name="text",
                fontName=self.styles["text"][0],
                fontSize=self.styles["text"][1] * self.FONT_SCALE,
                leading=self.styles["text"][1] * self.FONT_SCALE + 0.5 * mm,
                spaceBefore=1 * mm,
            )
        )

    def set_font(self, canvas, section, custom_scale=1.0):
        canvas.setFont(
            self.styles[section][0],
            self.styles[section][1] * self.FONT_SCALE * custom_scale,
        )
        return self.styles[section][1]

    def _register_fonts(self):
        raise NotImplementedError


class FreeFonts(Fonts):
    FONT_SCALE = 1.41

    styles = {
        "title": ("Universal Serif", 2.5 * mm, "black"),
        "subtitle": ("ScalySans", 1.5 * mm, "white"),
        "category": ("Universal Serif", 2.25 * mm, "black"),
        "subcategory": ("Universal Serif", 1.5 * mm, "black"),
        "text": ("ScalySans", 1.8 * mm, "black"),
        "artist": ("ScalySans", 1.5 * mm, "white"),
    }

    def _register_fonts(self):
        pdfmetrics.registerFont(
            TTFont("Universal Serif", self.FONT_DIR / "Universal Serif.ttf")
        )
        pdfmetrics.registerFont(TTFont("ScalySans", self.FONT_DIR / "ScalySans.ttf"))
        pdfmetrics.registerFont(
            TTFont("ScalySansItalic", self.FONT_DIR / "ScalySans-Italic.ttf")
        )
        pdfmetrics.registerFont(
            TTFont("ScalySansBold", self.FONT_DIR / "ScalySans-Bold.ttf")
        )
        pdfmetrics.registerFont(
            TTFont("ScalySansBoldItalic", self.FONT_DIR / "ScalySans-BoldItalic.ttf")
        )

        addMapping("ScalySans", 0, 0, "ScalySans")  # normal
        addMapping("ScalySans", 0, 1, "ScalySansItalic")  # italic
        addMapping("ScalySans", 1, 0, "ScalySansBold")  # bold
        addMapping("ScalySans", 1, 1, "ScalySansBoldItalic")  # italic and bold


class AccurateFonts(Fonts):
    FONT_SCALE = 1.41

    styles = {
        "title": ("ModestoExpanded", 2.5 * mm, "black"),
        "subtitle": ("ModestoTextLight", 1.5 * mm, "white"),
        "category": ("ModestoExpanded", 2.25 * mm, "black"),
        "subcategory": ("ModestoExpanded", 1.5 * mm, "black"),
        "text": ("ModestoTextLight", 1.8 * mm, "black"),
        "artist": ("ModestoTextLight", 1.25 * mm, "white"),
    }

    def _register_fonts(self):
        pdfmetrics.registerFont(
            TTFont("ModestoExpanded", self.FONT_DIR / "ModestoExpanded-Regular.ttf")
        )
        pdfmetrics.registerFont(
            TTFont("ModestoTextLight", self.FONT_DIR / "ModestoText-Light.ttf")
        )
        pdfmetrics.registerFont(
            TTFont(
                "ModestoTextLightItalic",
                self.FONT_DIR / "ModestoText-LightItalic.ttf",
            )
        )
        pdfmetrics.registerFont(
            TTFont("ModestoTextBold", self.FONT_DIR / "ModestoText-Bold.ttf")
        )
        pdfmetrics.registerFont(
            TTFont(
                "ModestoTextBoldItalic",
                self.FONT_DIR / "ModestoText-BoldItalic.ttf",
            )
        )

        addMapping("ModestoTextLight", 0, 0, "ModestoTextLight")  # normal
        addMapping("ModestoTextLight", 0, 1, "ModestoTextLightItalic")  # italic
        addMapping("ModestoTextLight", 1, 0, "ModestoTextBold")  # bold
        addMapping("ModestoTextLight", 1, 1, "ModestoTextBoldItalic")  # italic and bold
