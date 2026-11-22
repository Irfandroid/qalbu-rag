// Server-sent events reader used by the chat request.

const EVENT_FIELD = "event:";
const DATA_FIELD = "data:";
const BLOCK_SEPARATOR = "\n\n";
const DEFAULT_EVENT = "message";
const DEFAULT_DATA = "{}";

function parseBlock(block) {
  let event = DEFAULT_EVENT;
  let data = DEFAULT_DATA;
  for (const line of block.split("\n")) {
    if (line.startsWith(EVENT_FIELD)) event = line.slice(6).trim();
    if (line.startsWith(DATA_FIELD)) data = line.slice(5).trim();
  }
  return { event, data };
}

export async function consumeSSE(response, onEvent) {
  if (!response.ok) throw Error("Permintaan belum bisa diproses.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    let boundary;
    while ((boundary = buffer.indexOf(BLOCK_SEPARATOR)) >= 0) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + BLOCK_SEPARATOR.length);
      const { event, data } = parseBlock(block);
      onEvent(event, JSON.parse(data));
    }

    if (done) break;
  }
}
