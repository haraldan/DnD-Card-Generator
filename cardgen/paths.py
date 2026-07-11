import pathlib

# Assets (fonts, placeholder image) live alongside the repo root, next to the
# cardgen package. Paths are resolved relative to this file so the library works
# regardless of the current working directory (including inside the container).
ASSET_DIR = pathlib.Path(__file__).parent.parent.resolve() / "assets"
FONT_DIR = ASSET_DIR / "fonts"
PLACEHOLDER_ITEM = ASSET_DIR / "D20.png"
