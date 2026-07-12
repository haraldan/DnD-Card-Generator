"use strict";

// Aspect ratio of a small card's front image area (mm): (63-2.5-2.5) / (89-2.5-7.5)
const CROP_ASPECT = 58 / 79;
const AUTOSAVE_MS = 800;

const builder = document.getElementById("builder");
const libraryList = document.getElementById("library-list");
const libraryEmpty = document.getElementById("library-empty");
const previewFrame = document.getElementById("preview-frame");
const previewErrors = document.getElementById("preview-errors");

const saveTimers = new Map(); // id -> timeout handle

// ------------------------------------------------------------------ helpers
function uuid() {
  if (crypto && crypto.randomUUID) return crypto.randomUUID();
  // Fallback (non-secure contexts)
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

function serializeCard(node) {
  return {
    id: node.dataset.id,
    title: node.querySelector(".f-title").value,
    subtitle: node.querySelector(".f-subtitle").value,
    color: node.querySelector(".f-color").value,
    font_size: parseFloat(node.querySelector(".f-fontsize").value) || 8,
    description: node.querySelector(".f-description").value,
    copies: parseInt(node.querySelector(".f-copies").value) || 1,
  };
}

async function saveCopies(node) {
  const copies = parseInt(node.querySelector(".f-copies").value) || 1;
  await fetch(`/working/${node.dataset.id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ copies }),
  });
}

async function saveCard(node) {
  const card = serializeCard(node);
  await fetch(`/cards/${card.id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(card),
  });
  refreshLibrary();
}

function scheduleSave(node) {
  const id = node.dataset.id;
  clearTimeout(saveTimers.get(id));
  saveTimers.set(id, setTimeout(() => saveCard(node), AUTOSAVE_MS));
}

// ------------------------------------------------------------------ images
async function uploadImage(id, fileOrBlob, filename) {
  const fd = new FormData();
  fd.append("file", fileOrBlob, filename || fileOrBlob.name || "image.png");
  const res = await fetch(`/cards/${id}/image`, { method: "POST", body: fd });
  return res.ok;
}

function showThumb(node) {
  const id = node.dataset.id;
  const thumb = node.querySelector(".thumb");
  thumb.src = `/cards/${id}/image?t=${Date.now()}`;
  thumb.hidden = false;
  node.querySelector(".crop-btn").hidden = false;
  node.querySelector(".del-image").hidden = false;
}

function hideThumb(node) {
  node.querySelector(".thumb").hidden = true;
  node.querySelector(".crop-btn").hidden = true;
  node.querySelector(".del-image").hidden = true;
}

// ------------------------------------------------------------------ crop modal
const cropModal = document.getElementById("crop-modal");
const cropImage = document.getElementById("crop-image");
let cropper = null;
let cropTarget = null;

function openCrop(node) {
  cropTarget = node;
  const id = node.dataset.id;
  cropImage.src = node._objectUrl || `/cards/${id}/image?t=${Date.now()}`;
  cropModal.hidden = false;
  cropImage.onload = () => {
    if (cropper) cropper.destroy();
    cropper = new Cropper(cropImage, { aspectRatio: CROP_ASPECT, viewMode: 1, autoCropArea: 1 });
  };
}

function closeCrop() {
  if (cropper) { cropper.destroy(); cropper = null; }
  cropModal.hidden = true;
  cropTarget = null;
}

document.getElementById("crop-cancel").addEventListener("click", closeCrop);
document.getElementById("crop-apply").addEventListener("click", () => {
  if (!cropper || !cropTarget) return closeCrop();
  const node = cropTarget;
  cropper.getCroppedCanvas().toBlob(async (blob) => {
    if (blob) {
      await uploadImage(node.dataset.id, blob, "crop.png");
      node._objectUrl = null;
      showThumb(node);
    }
    closeCrop();
  }, "image/png");
});

// ------------------------------------------------------------------ card editor
function buildCard(data) {
  const tpl = document.getElementById("card-template");
  const node = tpl.content.firstElementChild.cloneNode(true);
  node.dataset.id = data.id;
  node.querySelector(".f-title").value = data.title || "";
  node.querySelector(".f-subtitle").value = data.subtitle || "";
  if (data.color) node.querySelector(".f-color").value = normalizeColor(data.color);
  node.querySelector(".f-description").value = data.description || "";
  node.querySelector(".f-fontsize").value = data.font_size || 8;
  node.querySelector(".reset-fontsize").addEventListener("click", () => {
    node.querySelector(".f-fontsize").value = 8;
    scheduleSave(node);
  });

  const copies = node.querySelector(".f-copies");
  copies.value = data.copies || 1;
  copies.addEventListener("change", () => saveCopies(node));

  if (data.has_image) showThumb(node);

  // Live autosave of card fields on any change
  node.addEventListener("input", () => scheduleSave(node));

  // The card's × removes it from the working list only (it stays saved on disk
  // and in the Library).
  node.querySelector(".del-card").addEventListener("click", async () => {
    await fetch(`/working/${node.dataset.id}`, { method: "DELETE" });
    node.remove();
    refreshLibrary();
  });

  const fileInput = node.querySelector(".f-image");
  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    if (!file) return;
    node._objectUrl = URL.createObjectURL(file);
    await uploadImage(node.dataset.id, file);
    showThumb(node);
  });
  node.querySelector(".crop-btn").addEventListener("click", () => openCrop(node));
  node.querySelector(".del-image").addEventListener("click", async () => {
    await fetch(`/cards/${node.dataset.id}/image`, { method: "DELETE" });
    node._objectUrl = null;
    hideThumb(node);
  });

  builder.appendChild(node);
  return node;
}

function normalizeColor(c) {
  // <input type=color> only accepts #rrggbb; leave hex as-is, otherwise default.
  return /^#[0-9a-fA-F]{6}$/.test(c) ? c : "#24394d";
}

function findCardNode(id) {
  return builder.querySelector(`.card-editor[data-id="${id}"]`);
}

// ------------------------------------------------------------------ library
async function refreshLibrary() {
  const res = await fetch("/cards");
  const cards = await res.json();
  libraryList.innerHTML = "";
  libraryEmpty.hidden = cards.length > 0;
  cards.forEach((c) => {
    const li = document.createElement("li");
    if (findCardNode(c.id)) li.classList.add("in-list");
    const a = document.createElement("a");
    a.textContent = c.title || "(untitled)";
    a.title = "Click to add to the render list · Right-click to duplicate";
    a.addEventListener("click", () => addToWorking(c.id));
    a.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      duplicateCard(c.id);
    });
    const del = document.createElement("button");
    del.className = "danger";
    del.textContent = "×";
    del.title = "Delete permanently";
    del.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm(`Delete "${c.title || "this card"}" permanently?`)) return;
      await fetch(`/cards/${c.id}`, { method: "DELETE" });
      const node = findCardNode(c.id);
      if (node) node.remove();
      refreshLibrary();
    });
    li.appendChild(a);
    li.appendChild(del);
    libraryList.appendChild(li);
  });
  updatePalette();
}

// Populate each card's colour swatches with the colours already in use.
async function updatePalette() {
  const colors = await (await fetch("/colors")).json();
  builder.querySelectorAll(".card-editor").forEach((node) => {
    const box = node.querySelector(".swatches");
    box.innerHTML = "";
    colors.forEach((col, i) => {
      const isDefault = i === 0; // the default colour is always first
      const b = document.createElement("button");
      b.type = "button";
      b.className = "swatch";
      b.style.background = col;
      b.title = isDefault
        ? `${col} (default)`
        : `${col} — click to use, right-click to remove`;
      b.addEventListener("click", () => {
        node.querySelector(".f-color").value = col;
        scheduleSave(node);
      });
      b.addEventListener("contextmenu", async (e) => {
        e.preventDefault(); // never show the browser menu on a swatch
        if (isDefault) return; // default colour can't be removed
        await fetch(`/colors?color=${encodeURIComponent(col)}`, { method: "DELETE" });
        updatePalette();
      });
      box.appendChild(b);
    });
  });
}

// Briefly highlight an element to make a value change visible.
function flash(el) {
  el.animate(
    [
      { backgroundColor: "#ffd666", transform: "scale(1.25)" },
      { backgroundColor: "#ffd666", transform: "scale(1.25)", offset: 0.15 },
      { backgroundColor: "", transform: "scale(1)" },
    ],
    { duration: 650, easing: "ease-out" }
  );
}

// Add a saved card to the working list, or bump its copies if already there.
async function addToWorking(id) {
  await fetch(`/working/${id}`, { method: "POST" });
  let node = findCardNode(id);
  if (node) {
    const f = node.querySelector(".f-copies");
    f.value = (parseInt(f.value) || 1) + 1;
    flash(f);
  } else {
    const res = await fetch(`/cards/${id}`);
    if (!res.ok) return;
    node = buildCard({ ...(await res.json()), copies: 1 });
    refreshLibrary();
  }
  node.scrollIntoView({ behavior: "smooth", block: "center" });
}

// Duplicate a saved card (content + artwork) into a new card and load it.
async function duplicateCard(id) {
  const res = await fetch(`/cards/${id}/duplicate`, { method: "POST" });
  if (!res.ok) return;
  const copy = buildCard(await res.json());
  refreshLibrary();
  copy.scrollIntoView({ behavior: "smooth", block: "center" });
}

// ------------------------------------------------------------------ toolbar
document.getElementById("add-card").addEventListener("click", async () => {
  const data = { id: uuid(), color: "#24394d", description: "", copies: 1 };
  const node = buildCard(data);
  await saveCard(node); // persist the new card to disk / Library
  await fetch(`/working/${data.id}`, { method: "POST" }); // add to render list
  refreshLibrary();
  node.querySelector(".f-title").focus();
});

async function renderTo(url, disposition) {
  const busy = document.getElementById("busy");
  busy.hidden = false;
  try {
    const cards = Array.from(builder.querySelectorAll(".card-editor")).map(serializeCard);
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cards }),
    });
    const errs = res.headers.get("X-Card-Errors");
    previewErrors.hidden = !errs;
    if (errs) previewErrors.textContent = "Could not fit: " + errs;
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  } finally {
    busy.hidden = true;
  }
}

document.getElementById("preview").addEventListener("click", async () => {
  previewFrame.src = await renderTo("/preview");
});

document.getElementById("download").addEventListener("click", async () => {
  const url = await renderTo("/download");
  const a = document.createElement("a");
  a.href = url;
  a.download = "cards.pdf";
  a.click();
});

// ------------------------------------------------------------------ init
async function init() {
  // The working list = cards currently loaded for rendering (each with copies).
  const working = await (await fetch("/working")).json();
  working.forEach((card) => buildCard(card));

  if (working.length === 0) {
    // Nothing loaded. If there are no saved cards at all, start with a blank
    // one; otherwise leave the builder empty so the user can pick from the
    // Library.
    const lib = await (await fetch("/cards")).json();
    if (lib.length === 0) {
      const data = { id: uuid(), color: "#24394d", description: "", copies: 1 };
      const node = buildCard(data);
      await saveCard(node);
      await fetch(`/working/${data.id}`, { method: "POST" });
    }
  }
  refreshLibrary();
}

init();
