// Chat form: submit reflections, stream events, and render the result.

import { createChatRenderer } from "./chat-render.js";
import { consumeSSE } from "./sse.js";

const MIN_COMPOSER_HEIGHT = 44;
const MAX_COMPOSER_HEIGHT = 150;
const NETWORK_ERROR_MESSAGE =
  "Backend Qalbu tidak terhubung. Jalankan server lokal, lalu coba lagi.";
const GENERIC_ERROR_MESSAGE = "Terjadi kendala. Coba lagi.";
const EMPTY_RESULT_MESSAGE = "Refleksi belum tersedia. Coba lagi.";

const form = document.querySelector("#chat-form");
const message = document.querySelector("#message");
const send = document.querySelector("#send");
const result = document.querySelector("#result");
const conversation = document.querySelector("#conversation");

let lastMessage = "";

const renderer = createChatRenderer({
  result,
  conversation,
  onRetry: () => submit(lastMessage),
});

function resizeComposer() {
  message.style.height = "auto";
  message.style.height =
    Math.min(
      MAX_COMPOSER_HEIGHT,
      Math.max(MIN_COMPOSER_HEIGHT, message.scrollHeight),
    ) + "px";
}

function handleStreamEvent(event, data, markSettled) {
  if (event === "response") {
    renderer.renderResponse(data);
    markSettled();
  } else if (event === "crisis") {
    renderer.renderCrisis(data);
    markSettled();
  } else if (event === "error") {
    renderer.renderError(data.message || GENERIC_ERROR_MESSAGE);
    markSettled();
  } else if (event === "done") {
    renderer.renderError(EMPTY_RESULT_MESSAGE);
    markSettled();
  }
}

async function submit(value) {
  const text = (value || message.value).trim();
  if (!text) return;

  let settled = false;
  const markSettled = () => {
    settled = true;
  };
  lastMessage = text;
  message.value = "";
  resizeComposer();
  send.disabled = true;
  renderer.addUser(text);
  renderer.showLoading();

  try {
    const response = await fetch("/api/v1/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ message: text }),
    });
    await consumeSSE(response, (event, data) => {
      if (event === "done" && settled) return;
      handleStreamEvent(event, data, markSettled);
    });
  } catch (error) {
    renderer.renderError(
      error instanceof TypeError
        ? NETWORK_ERROR_MESSAGE
        : error.message || GENERIC_ERROR_MESSAGE,
    );
  } finally {
    send.disabled = false;
    message.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  submit();
});

message.addEventListener("input", resizeComposer);
message.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    submit();
  }
});

document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => {
    message.value = button.textContent;
    resizeComposer();
    message.focus();
  });
});

resizeComposer();
