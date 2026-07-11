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
        entries.append(storage.entry_for_render(native))
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
