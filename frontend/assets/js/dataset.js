// Dataset catalog: stats, filters, verse list, and manual request form.

const MAX_REFERENCE_LENGTH = 300;
const MAX_REASON_LENGTH = 500;

const search = document.querySelector("#search");
const category = document.querySelector("#category");
const results = document.querySelector("#results");
const matchCount = document.querySelector("#match-count");
const sourceNote = document.querySelector("#source-note");
const stats = document.querySelector("#stats");
const requestForm = document.querySelector("#request-form");
const requestReference = document.querySelector("#request-reference");
const requestReason = document.querySelector("#request-reason");
const requestStatus = document.querySelector("#request-status");
const requestOutput = document.querySelector("#request-output");

let catalog = null;

const formatNumber = (value) => new Intl.NumberFormat("id-ID").format(value);

function setStats(data) {
  const childTotal = Object.values(data.child_counts || {}).reduce(
    (sum, value) => sum + value,
    0,
  );
  const values = stats.querySelectorAll(".stat strong");
  values[0].textContent = formatNumber(data.parent_count);
  values[1].textContent = formatNumber(childTotal);
  values[2].textContent = formatNumber(data.reflection_subset);
}

function matchesFilters(item, query, wantedCategory) {
  const matchesQuery =
    !query ||
    item.verse_key.includes(query) ||
    item.surah_name.toLowerCase().includes(query);
  const matchesCategory =
    !wantedCategory ||
    item.categories.some((value) => value.id === wantedCategory);
  return matchesQuery && matchesCategory;
}

function buildVerseChip(item) {
  const chip = document.createElement("a");
  chip.className = "verse" + (item.in_reflection_subset ? " subset" : "");
  chip.href = "/dataset/verse/" + item.surah_number + "/" + item.ayah_number;
  chip.title =
    item.categories.map((value) => value.label).join(", ") ||
    "Buka detail ayat";
  chip.append(elementText("small", "Ayat " + item.ayah_number));
  if (item.categories.length) {
    chip.append(
      elementText(
        "span",
        "· " + item.categories.length + " kategori",
        "category",
      ),
    );
  }
  return chip;
}

function elementText(tag, text, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = text;
  return node;
}

function buildSurahSection(items, surahNumber) {
  const section = document.createElement("section");
  section.className = "surah";
  const head = document.createElement("div");
  head.className = "surah-head";
  const list = document.createElement("div");
  list.className = "verses";

  head.append(
    elementText("h2", items[0].surah_name),
    elementText("p", "Surah " + surahNumber + " · " + items.length + " ayat"),
  );
  for (const item of items) list.append(buildVerseChip(item));
  section.append(head, list);
  return section;
}

function render() {
  if (!catalog) return;

  const query = search.value.trim().toLowerCase();
  const wantedCategory = category.value;
  const verses = catalog.verses.filter((item) =>
    matchesFilters(item, query, wantedCategory),
  );
  matchCount.textContent = formatNumber(verses.length) + " ayat cocok";
  results.replaceChildren();

  if (!verses.length) {
    results.append(
      elementText("p", "Tidak ada ayat yang cocok dengan filter ini.", "empty"),
    );
    return;
  }

  const bySurah = new Map();
  for (const item of verses) {
    if (!bySurah.has(item.surah_number)) bySurah.set(item.surah_number, []);
    bySurah.get(item.surah_number).push(item);
  }
  bySurah.forEach((items, surahNumber) => {
    results.append(buildSurahSection(items, surahNumber));
  });
}

function today() {
  return new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Jakarta" }).format(
    new Date(),
  );
}

function buildRequest() {
  return (
    "Request Tambah Dataset Qalbu\n\n" +
    "Referensi:\n" +
    requestReference.value.trim() +
    "\n\nAlasan:\n" +
    requestReason.value.trim() +
    "\n\nTanggal: " +
    today()
  );
}

function showRequestError(message, field) {
  requestStatus.className = "request-status error";
  requestStatus.textContent = message;
  field.focus();
}

function showClipboardFallback() {
  requestStatus.textContent = "Clipboard tidak tersedia. Salin teks di bawah.";
  requestOutput.focus();
  requestOutput.select();
}

function validateRequest(reference, reason) {
  if (!reference) {
    showRequestError("Isi ayat atau surat terlebih dahulu.", requestReference);
    return false;
  }
  if (reference.length > MAX_REFERENCE_LENGTH) {
    showRequestError("Referensi maksimal 300 karakter.", requestReference);
    return false;
  }
  if (!reason) {
    showRequestError(
      "Isi alasan atau topik request terlebih dahulu.",
      requestReason,
    );
    return false;
  }
  if (reason.length > MAX_REASON_LENGTH) {
    showRequestError("Alasan maksimal 500 karakter.", requestReason);
    return false;
  }
  return true;
}

function copyRequest(text) {
  requestOutput.value = text;
  requestOutput.hidden = false;
  requestStatus.className = "request-status";

  if (
    !window.isSecureContext ||
    typeof navigator.clipboard?.writeText !== "function"
  ) {
    showClipboardFallback();
    return;
  }

  navigator.clipboard
    .writeText(text)
    .then(() => {
      requestStatus.textContent =
        "Request tersalin. Kirim teks ini untuk ditambahkan manual.";
    })
    .catch(showClipboardFallback);
}

requestForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const reference = requestReference.value.trim();
  const reason = requestReason.value.trim();
  if (!validateRequest(reference, reason)) return;
  copyRequest(buildRequest());
});

function populateCategories(options) {
  options.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.label;
    category.append(option);
  });
}

function showCatalogError(error) {
  matchCount.textContent = "";
  sourceNote.textContent = "";
  results.append(elementText("p", error.message, "error"));
}

async function load() {
  try {
    const response = await fetch("/api/v1/dataset/verses");
    if (!response.ok) throw new Error("Katalog belum dapat dimuat.");
    catalog = await response.json();
    setStats(catalog);
    populateCategories(catalog.category_options);
    sourceNote.textContent =
      "Corpus " +
      catalog.corpus +
      " · " +
      catalog.source.authority +
      " · diverifikasi " +
      (catalog.verified_at || "sumber resmi");
    render();
  } catch (error) {
    showCatalogError(error);
  }
}

search.addEventListener("input", render);
category.addEventListener("change", render);
load();
