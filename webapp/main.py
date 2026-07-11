import io
import logging
import mimetypes
import pathlib
from typing import List

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cardgen import render_item_cards, RenderOptions, get_provider
from cardgen.layout import DEFAULT_COLOR

from . import storage
from .schema import CardIn, to_native, to_browser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = pathlib.Path(__file__).parent.parent
INDEX_HTML = (BASE_DIR / "templates" / "index.html").read_text()

MAX_IMAGE_BYTES = 8 * 1024 * 1024

app = FastAPI(title="D&D Item Card Generator")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.on_event("startup")
def _startup():
    storage.init_storage()


class CardWithId(CardIn):
    id: str
    copies: int = 1


class Deck(BaseModel):
    cards: List[CardWithId] = []


def _valid_id_or_404(card_id: str) -> str:
    try:
        import uuid

        return str(uuid.UUID(card_id))
    except ValueError:
        raise HTTPException(status_code=404, detail="invalid card id")


# ---------------------------------------------------------------- pages
@app.get("/", response_class=HTMLResponse)
def index():
    flag = "true" if get_provider() is not None else "false"
    return HTMLResponse(INDEX_HTML.replace("__HAS_IMAGE_PROVIDER__", flag))


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# ---------------------------------------------------------------- cards CRUD
@app.get("/cards")
def list_cards():
    return storage.list_cards()


@app.get("/colors")
def colors():
    # Always offer the default colour first, then the ones already in use.
    used = storage.used_colors()
    return [DEFAULT_COLOR] + [c for c in used if c != DEFAULT_COLOR]


@app.get("/cards/{card_id}")
def get_card(card_id: str):
    _valid_id_or_404(card_id)
    entry = storage.load_card(card_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="card not found")
    return to_browser(entry)


@app.put("/cards/{card_id}")
def put_card(card_id: str, card: CardIn):
    _valid_id_or_404(card_id)
    storage.save_card(card_id, to_native(card))
    return {"ok": True, "has_image": storage.image_file(card_id) is not None}


@app.delete("/cards/{card_id}")
def remove_card(card_id: str):
    _valid_id_or_404(card_id)
    storage.delete_card(card_id)
    return {"ok": True}


# ---------------------------------------------------------------- working list
@app.get("/working")
def get_working():
    """The current render list: each saved card plus how many copies."""
    out = []
    for entry in storage.load_working():
        card = storage.load_card(entry["id"])
        if card is None:
            continue
        out.append({**to_browser(card), "copies": entry["copies"]})
    return out


@app.post("/working/{card_id}")
def working_add(card_id: str):
    _valid_id_or_404(card_id)
    storage.add_working(card_id)
    return {"ok": True}


class Copies(BaseModel):
    copies: int = 1


@app.put("/working/{card_id}")
def working_set_copies(card_id: str, body: Copies):
    _valid_id_or_404(card_id)
    storage.set_working_copies(card_id, body.copies)
    return {"ok": True}


@app.delete("/working/{card_id}")
def working_remove(card_id: str):
    _valid_id_or_404(card_id)
    storage.remove_working(card_id)
    return {"ok": True}


# ---------------------------------------------------------------- images
@app.post("/cards/{card_id}/image")
async def upload_image(card_id: str, file: UploadFile = File(...)):
    _valid_id_or_404(card_id)
    ext = pathlib.Path(file.filename or "").suffix.lower()
    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="image too large (max 8MB)")
    try:
        storage.save_image(card_id, ext, data)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc))
    # Re-persist the card (if it exists) so its YAML records the image path.
    existing = storage.load_card(card_id)
    if existing is not None:
        storage.save_card(card_id, existing)
    return {"ok": True}


@app.get("/cards/{card_id}/image")
def get_image(card_id: str):
    _valid_id_or_404(card_id)
    img = storage.image_file(card_id)
    if img is None:
        raise HTTPException(status_code=404, detail="no image")
    media = mimetypes.guess_type(str(img))[0] or "application/octet-stream"
    return FileResponse(str(img), media_type=media)


@app.delete("/cards/{card_id}/image")
def delete_image(card_id: str):
    _valid_id_or_404(card_id)
    img = storage.image_file(card_id)
    if img is not None:
        img.unlink()
    existing = storage.load_card(card_id)
    if existing is not None:
        storage.save_card(card_id, existing)
    return {"ok": True}


# ---------------------------------------------------------------- rendering
def _render_deck(deck: Deck) -> tuple[bytes, list]:
    entries = []
    for card in deck.cards:
        native = to_native(card)
        native["_id"] = card.id
        entry = storage.entry_for_render(native)
        # Render the card `copies` times (min 1).
        for _ in range(max(1, int(card.copies or 1))):
            entries.append(entry)
    options = RenderOptions()
    pdf = render_item_cards(entries, options)
    return pdf, options.errors


@app.post("/preview")
def preview(deck: Deck):
    pdf, errors = _render_deck(deck)
    headers = {"Content-Disposition": "inline; filename=cards.pdf"}
    if errors:
        headers["X-Card-Errors"] = "; ".join(errors)
    return Response(content=pdf, media_type="application/pdf", headers=headers)


@app.post("/download")
def download(deck: Deck):
    pdf, errors = _render_deck(deck)
    headers = {"Content-Disposition": "attachment; filename=cards.pdf"}
    if errors:
        headers["X-Card-Errors"] = "; ".join(errors)
    return Response(content=pdf, media_type="application/pdf", headers=headers)
