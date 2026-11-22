// Homepage daily verse: load the verse of the day and rotate at Jakarta midnight.

const ENDPOINT = "/api/v1/dataset/verse-of-day";
const JAKARTA_OFFSET_MS = 7 * 60 * 60 * 1000;
const MIN_ROTATION_DELAY_MS = 1000;
const MISSING_SURAH_NAME = /^Surah\s+\d+$/i;

const state = document.querySelector("#daily-verse-state");
let rotationTimer;

function scheduleRotation() {
  clearTimeout(rotationTimer);
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Jakarta",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  })
    .formatToParts(new Date())
    .reduce((result, item) => {
      result[item.type] = item.value;
      return result;
    }, {});
  const tomorrow =
    Date.UTC(
      Number(parts.year),
      Number(parts.month) - 1,
      Number(parts.day) + 1,
    ) - JAKARTA_OFFSET_MS;
  rotationTimer = setTimeout(
    load,
    Math.max(
      MIN_ROTATION_DELAY_MS,
      tomorrow - Date.now() + MIN_ROTATION_DELAY_MS,
    ),
  );
}

function surahSuffix(name) {
  return name && !MISSING_SURAH_NAME.test(name) ? " · " + name : "";
}

function render(data) {
  state.className = "daily-verse-content";
  state.replaceChildren();

  const reference = document.createElement("strong");
  reference.className = "daily-verse-reference";
  reference.textContent =
    "QS. " +
    data.surah_number +
    ":" +
    data.ayah_number +
    surahSuffix(data.surah_name);

  const translation = document.createElement("span");
  translation.className = "daily-verse-translation";
  translation.textContent = data.translation || "Terjemahan belum tersedia.";
  translation.title = translation.textContent;

  const link = document.createElement("a");
  link.className = "daily-verse-link";
  link.href = data.detail_url;
  link.textContent = "Buka ayat →";

  const source = document.createElement("small");
  source.className = "daily-verse-source";
  source.textContent = data.source_status || "Status sumber tidak tersedia";

  state.append(reference, translation, link, source);
  scheduleRotation();
}

function renderError() {
  state.className = "daily-verse-error";
  state.replaceChildren(
    document.createTextNode("Ayat hari ini belum dapat dimuat."),
  );
  const retry = document.createElement("button");
  retry.type = "button";
  retry.className = "daily-verse-retry";
  retry.textContent = "Coba lagi";
  retry.onclick = load;
  state.append(retry);
}

async function load() {
  state.className = "daily-verse-error";
  state.textContent = "Memuat ayat…";
  try {
    const response = await fetch(ENDPOINT);
    if (!response.ok) throw Error("daily verse unavailable");
    render(await response.json());
  } catch {
    renderError();
  }
}

load();
