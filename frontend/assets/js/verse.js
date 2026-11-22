// Dataset verse detail: read surah/ayah from the path and render the verse card.

const statusNode = document.querySelector("#status");
const card = document.querySelector("#verse-card");
const title = document.querySelector("#title");

const pathParts = location.pathname.split("/").filter(Boolean);
const endpoint =
  "/api/v1/dataset/verses/" +
  encodeURIComponent(pathParts.at(-2)) +
  "/" +
  encodeURIComponent(pathParts.at(-1));

function element(tag, value, className) {
  const node = document.createElement(tag);
  node.textContent = value || "";
  if (className) node.className = className;
  return node;
}

function showError(message) {
  statusNode.className = "status error";
  statusNode.replaceChildren(element("span", message));
  const retry = document.createElement("button");
  retry.type = "button";
  retry.className = "retry";
  retry.textContent = "Coba lagi";
  retry.onclick = load;
  statusNode.append(retry);
}

function render(data) {
  title.textContent =
    data.surah_name + " " + data.surah_number + ":" + data.ayah_start;
  statusNode.hidden = true;

  const head = document.createElement("header");
  head.className = "verse-head";
  head.append(
    element("h2", data.surah_name),
    element("span", data.surah_number + ":" + data.ayah_start),
  );

  const arabic = element(
    "blockquote",
    data.arabic_text || "Teks Arab belum tersedia",
    "arabic",
  );
  arabic.lang = "ar";
  arabic.dir = "rtl";

  const translation = element(
    "p",
    data.translation || "Terjemahan belum tersedia",
    "translation",
  );
  card.append(head, arabic, translation);

  if (data.tafsir) {
    const section = document.createElement("details");
    section.className = "section";
    section.append(
      element("summary", "Baca tafsir sumber"),
      element("p", data.tafsir),
    );
    card.append(section);
  }

  card.append(element("small", data.source_status, "source"));
  card.hidden = false;
}

async function load() {
  statusNode.hidden = false;
  statusNode.className = "status";
  statusNode.textContent = "Memuat detail ayat…";
  card.replaceChildren();
  card.hidden = true;

  try {
    const response = await fetch(endpoint);
    let body = {};
    try {
      body = await response.json();
    } catch {
      body = {};
    }
    if (!response.ok) {
      throw new Error(
        body.detail?.message || "Detail ayat belum dapat dimuat.",
      );
    }
    render(body);
  } catch (error) {
    showError(error.message);
  }
}

load();
