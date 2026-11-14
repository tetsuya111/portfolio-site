export type SseEvent = { event: string; data: unknown };

/** SSEのテキストを少しずつ受け取り、完結したイベントだけを返すパーサー。 */
export function createSseParser() {
  let buffer = "";
  return (chunk: string): SseEvent[] => {
    buffer += chunk.replace(/\r\n/g, "\n");
    const events: SseEvent[] = [];
    let index: number;
    while ((index = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, index);
      buffer = buffer.slice(index + 2);
      let event = "message";
      const data: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
      }
      if (data.length > 0) events.push({ event, data: JSON.parse(data.join("\n")) });
    }
    return events;
  };
}
