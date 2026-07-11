import os
from typing import Callable, Optional, Protocol

from .paths import PLACEHOLDER_ITEM


class ImageProvider(Protocol):
    """Optional pluggable image-generation backend.

    No concrete provider ships with the app. A future provider would implement
    `generate` and register itself in `_REGISTRY`; it is selected via the
    `CARDGEN_IMAGE_PROVIDER` environment variable. Note: the Claude API cannot
    generate images, so any provider added here is a third-party service.
    """

    def generate(self, prompt: str, *, width: int, height: int) -> bytes: ...


# Registry of provider factories, keyed by the CARDGEN_IMAGE_PROVIDER value.
# Intentionally empty — the app is fully functional without an image provider.
_REGISTRY: dict[str, Callable[[], ImageProvider]] = {}


def get_provider() -> Optional[ImageProvider]:
    name = os.environ.get("CARDGEN_IMAGE_PROVIDER")
    if not name:
        return None
    factory = _REGISTRY.get(name)
    return factory() if factory else None


def resolve_image(entry: dict, upload_path: Optional[str] = None) -> str:
    """Return the image path to render for a card entry, falling back to the
    bundled placeholder when the card has no image."""
    if upload_path:
        return upload_path
    if entry.get("image_path"):
        return str(entry["image_path"])
    return str(PLACEHOLDER_ITEM)
