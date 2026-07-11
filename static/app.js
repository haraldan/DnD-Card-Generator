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
  };
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

  if (data.has_image) showThumb(node);

  // Live autosave on any field change
  node.addEventListener("input", () => scheduleSave(node));

  node.querySelector(".del-card").addEventListener("click", async () => {
    await fetch(`/cards/${node.dataset.id}`, { method: "DELETE" });
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
  return /^#[0-9a-fA-F]{6}$/.test(c) ? c : "#2f4a63";
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
    const a = document.createElement("a");
    a.textContent = c.title || "(untitled)";
    a.title = c.title || "(untitled)";
    a.addEventListener("click", () => loadCardIntoBuilder(c.id));
    const del = document.createElement("button");
    del.className = "danger";
    del.textContent = "×";
    del.title = "Delete";
    del.addEventListener("click", async (e) => {
      e.stopPropagation();
      await fetch(`/cards/${c.id}`, { method: "DELETE" });
      const node = findCardNode(c.id);
      if (node) node.remove();
      refreshLibrary();
    });
    li.appendChild(a);
    li.appendChild(del);
    libraryList.appendChild(li);
  });
}

async function loadCardIntoBuilder(id) {
  let node = findCardNode(id);
  if (node) {
    node.scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }
  const res = await fetch(`/cards/${id}`);
  if (!res.ok) return;
  node = buildCard(await res.json());
  node.scrollIntoView({ behavior: "smooth", block: "center" });
}

// ------------------------------------------------------------------ toolbar
document.getElementById("add-card").addEventListener("click", () => {
  const data = { id: uuid(), color: "#2f4a63", description: [] };
  const node = buildCard(data);
  saveCard(node); // persist immediately so it appears in the library
  node.querySelector(".f-title").focus();
});

async function renderTo(url, disposition) {
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
  const res = await fetch("/cards");
  const cards = await res.json();
  for (const c of cards) {
    const full = await (await fetch(`/cards/${c.id}`)).json();
    buildCard(full);
  }
  if (cards.length === 0) {
    buildCard({ id: uuid(), color: "#2f4a63", description: [] });
  }
  refreshLibrary();
}

init();
