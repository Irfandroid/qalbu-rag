// Local-only chat history: snapshot the conversation, restore it, and list sessions.

const STORAGE_KEY = "qalbu.chat-history.v1";
const MAX_SESSIONS = 12;
const SAVE_DEBOUNCE_MS = 120;
const TITLE_LENGTH = 42;
const UNSAFE_RESTORE_SELECTOR = "script,iframe,object,embed,link";

const conversation = document.querySelector("#conversation");
const resultNode = document.querySelector("#result");
const historyList = document.querySelector("#history-list");
const newChatButtons = document.querySelectorAll("#new-chat,#new-chat-sidebar");
const sendButton = document.querySelector("#send");
const messageInput = document.querySelector("#message");

let sessions = [];
let currentId = "";
let saveTimer = null;
let storageAvailable = true;

function historyNodes() {
  return [...conversation.children].filter(
    (node) => node !== resultNode && node.id !== "daily-verse",
  );
}

function snapshot() {
  return historyNodes()
    .map((node) => node.outerHTML)
    .join("");
}

const introHtml = snapshot();

function loadSessions() {
  try {
    sessions = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]")
      .filter((item) => item && item.id && typeof item.html === "string")
      .slice(0, MAX_SESSIONS);
  } catch {
    storageAvailable = false;
  }
}

function save() {
  if (!storageAvailable) return;
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(sessions.slice(0, MAX_SESSIONS)),
    );
  } catch {
    storageAvailable = false;
  }
}

function currentSession() {
  return sessions.find((item) => item.id === currentId);
}

function sessionTitle() {
  const firstUser = conversation.querySelector(".message-row.user .bubble p");
  return firstUser?.textContent?.trim().slice(0, TITLE_LENGTH) || "Chat baru";
}

function persist() {
  const item = currentSession();
  if (!item) return;
  item.html = snapshot();
  item.title = sessionTitle();
  item.updatedAt = Date.now();
  save();
  renderHistory();
}

function newSession() {
  const now = Date.now();
  return {
    id: now.toString(36) + Math.random().toString(36).slice(2, 7),
    title: "Chat baru",
    html: introHtml,
    updatedAt: now,
  };
}

function renderHistory() {
  historyList.replaceChildren();
  if (!sessions.length) {
    const empty = document.createElement("p");
    empty.className = "history-empty";
    empty.textContent = "Belum ada chat tersimpan.";
    historyList.append(empty);
    return;
  }

  const sorted = sessions
    .slice()
    .sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
  for (const item of sorted) {
    const row = document.createElement("div");
    row.className = "history-item";
    const button = document.createElement("button");
    button.className =
      "history-button" + (item.id === currentId ? " active" : "");
    button.type = "button";
    button.textContent = item.title || "Chat baru";
    button.title = button.textContent;
    button.onclick = () => {
      if (sendButton.disabled) return;
      restore(item);
    };
    row.append(button);
    historyList.append(row);
  }
}

function stripUnsafeNodes(fragment) {
  fragment
    .querySelectorAll(UNSAFE_RESTORE_SELECTOR)
    .forEach((node) => node.remove());
  fragment.querySelectorAll("*").forEach((node) => {
    [...node.attributes]
      .filter((attribute) => attribute.name.startsWith("on"))
      .forEach((attribute) => node.removeAttribute(attribute.name));
  });
}

function restore(item) {
  currentId = item.id;
  while (
    resultNode.previousSibling &&
    resultNode.previousSibling.id !== "daily-verse"
  ) {
    resultNode.previousSibling.remove();
  }

  const template = document.createElement("template");
  template.innerHTML = item.html || introHtml;
  stripUnsafeNodes(template.content);
  resultNode.before(template.content);
  renderHistory();
  conversation.scrollTop = conversation.scrollHeight;
  messageInput.focus();
}

function startFreshChat() {
  if (sendButton.disabled) return;
  const item = newSession();
  sessions = [item, ...sessions].slice(0, MAX_SESSIONS);
  currentId = item.id;
  restore(item);
  save();
}

loadSessions();

if (!sessions.length) {
  const item = newSession();
  sessions = [item];
  currentId = item.id;
  save();
} else {
  const latest = sessions
    .slice()
    .sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0))[0];
  restore(latest);
}

newChatButtons.forEach((button) =>
  button.addEventListener("click", startFreshChat),
);

const observer = new MutationObserver(() => {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(persist, SAVE_DEBOUNCE_MS);
});
observer.observe(conversation, { childList: true });
window.addEventListener("beforeunload", persist);
renderHistory();
