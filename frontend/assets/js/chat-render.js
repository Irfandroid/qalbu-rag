// DOM rendering for chat messages, citations, and safety responses.

const AVATAR_TEXT = "Q";
const FALLBACK_PATTERN =
  /refleksi ai (sedang )?(tidak tersedia|belum tersedia)/i;
const DEFAULT_TRANSLATION_NAME = "Terjemahan Indonesia";
const MISSING_TRANSLATION =
  "Terjemahan Indonesia belum tersedia pada sumber ini.";
const MISSING_ARABIC = "Teks Arab tidak tersedia pada sumber ini.";
const MISSING_TAFSIR = "Tafsir tidak tersedia pada sumber ini.";
const WHY_SOURCE =
  "Qalbu mencocokkan konteks ceritamu dengan sumber yang tersedia. " +
  "Kamu tetap bebas menilai apakah kaitannya terasa relevan.";

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function avatar() {
  const node = element("span", "avatar", AVATAR_TEXT);
  node.setAttribute("aria-hidden", "true");
  return node;
}

function verseRange(reference) {
  return reference.ayah_start === reference.ayah_end
    ? "Ayat " + reference.ayah_start
    : "Ayat " + reference.ayah_start + "–" + reference.ayah_end;
}

function buildReference(reference) {
  const row = element("div", "reference");
  row.append(element("span", "", reference.surah_name));
  row.append(element("small", "", verseRange(reference)));
  return row;
}

function buildEvidence(source) {
  const card = element("section", "evidence");
  const head = element("div", "evidence-head");
  const name = element("span", "", "Al-Qur’an · " + source.surah_name);
  const ayah = element(
    "small",
    "",
    source.surah_number +
      ":" +
      source.ayah_start +
      (source.ayah_end !== source.ayah_start ? "–" + source.ayah_end : ""),
  );
  head.append(name, ayah);

  const arabic = element(
    "blockquote",
    "arabic",
    source.arabic_text || MISSING_ARABIC,
  );
  arabic.lang = "ar";
  arabic.dir = "rtl";
  arabic.translate = false;

  const translation = element("p", "translation");
  translation.lang = "id";
  translation.textContent = source.translation
    ? (source.translation_name || DEFAULT_TRANSLATION_NAME) +
      ": " +
      source.translation
    : MISSING_TRANSLATION;

  const tafsir = element("details", "tafsir");
  tafsir.append(
    element(
      "summary",
      "",
      source.tafsir ? "Baca tafsir sumber" : "Tafsir belum tersedia",
    ),
    element("p", "", source.tafsir || MISSING_TAFSIR),
  );

  const status = element("small", "evidence-status", source.source_status);
  card.append(head, arabic, translation, tafsir, status);
  return card;
}

function buildSources(data) {
  const references = data.references || [];
  const evidence = data.evidence || [];
  const section = element("section", "references");
  const why = element("details", "why-source");
  why.append(
    element("summary", "", "Mengapa sumber ini muncul?"),
    element("p", "", WHY_SOURCE),
  );
  section.append(
    element("div", "references-title", "Ayat dan tafsir untuk direnungkan"),
    why,
  );

  if (!evidence.length) {
    for (const reference of references)
      section.append(buildReference(reference));
  }
  for (const source of evidence) section.append(buildEvidence(source));

  if (data.safety_note) {
    section.append(element("small", "evidence-status", data.safety_note));
  }
  return section;
}

function buildMessageRow(kind) {
  const row = element("article", "message-row " + kind);
  return row;
}

export function createChatRenderer({ result, conversation, onRetry }) {
  let pendingRow = null;

  function scrollToLatest() {
    conversation.scrollTop = conversation.scrollHeight;
  }

  function clearPending() {
    if (!pendingRow) return;
    pendingRow.remove();
    pendingRow = null;
  }

  function addUser(text) {
    const item = buildMessageRow("user");
    const bubble = element("div", "bubble");
    bubble.append(element("p", "", text), element("small", "meta", "KAMU"));
    item.append(bubble);
    result.before(item);
    scrollToLatest();
  }

  function showLoading() {
    clearPending();
    const item = buildMessageRow("assistant");
    const bubble = element("div", "bubble skeleton");
    bubble.setAttribute("aria-label", "Qalbu sedang menyiapkan refleksi");
    bubble.innerHTML =
      '<div class="bone"></div><div class="bone"></div><div class="bone"></div>';
    item.append(avatar(), bubble);
    result.before(item);
    pendingRow = item;
    scrollToLatest();
  }

  function renderResponse(data) {
    clearPending();
    const isFallback = FALLBACK_PATTERN.test(data.answer || "");
    const hasSources =
      (data.references || []).length > 0 ||
      (data.evidence || []).length > 0 ||
      Boolean(data.safety_note);

    const item = buildMessageRow("assistant");
    const bubble = element("div", "bubble" + (isFallback ? " fallback" : ""));
    bubble.append(
      element(
        "div",
        "response-kicker",
        isFallback ? "Sumber untuk direnungkan" : "Ruang refleksi",
      ),
      element("p", "reflection-text", data.answer || ""),
    );
    if (!isFallback) {
      bubble.append(
        element(
          "small",
          "meta reflection-attribution",
          "Refleksi AI · sumber ditampilkan di bawah",
        ),
      );
    }
    if (hasSources) bubble.append(buildSources(data));
    bubble.append(
      element(
        "small",
        "meta",
        isFallback ? "QALBU · SUMBER SAJA" : "QALBU · SUMBER TERSEDIA DI ATAS",
      ),
    );
    item.append(avatar(), bubble);
    result.before(item);
    scrollToLatest();
  }

  function renderError(text) {
    clearPending();
    const item = buildMessageRow("assistant");
    const bubble = element("div", "bubble error");
    const retry = element("button", "retry", "Coba lagi");
    retry.type = "button";
    retry.onclick = onRetry;
    bubble.append(element("p", "", text), retry);
    item.append(avatar(), bubble);
    result.before(item);
    scrollToLatest();
  }

  function renderCrisis(data) {
    clearPending();
    const item = buildMessageRow("assistant");
    const bubble = element("div", "bubble crisis");
    bubble.setAttribute("role", "alert");
    const title = element("strong", "", "Bantuan segera");
    const copy = element("p", "", data.message);
    bubble.append(title, copy);
    if (data.tel) {
      const call = element("a", "retry", "Hubungi " + data.crisis_line);
      call.href = data.tel;
      bubble.append(call);
    }
    item.append(avatar(), bubble);
    result.before(item);
    title.tabIndex = -1;
    title.focus();
    scrollToLatest();
  }

  return { addUser, showLoading, renderResponse, renderError, renderCrisis };
}
