export type ContentPart = { type: "markdown"; text: string } | { type: "html"; html: string };

const HTML_BLOCK = /```html[ \t]*\n([\s\S]*?)```/g;

// 依頼者の入力が混ざったHTMLを表示するため、スクリプト・外部への通信をすべて禁じる
export const MOCK_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data:";

/** 本文を、通常のマークダウンと「画面のイメージ」（htmlのコードブロック）に分ける。 */
export function splitContent(content: string): ContentPart[] {
  const parts: ContentPart[] = [];
  let last = 0;
  for (const match of content.matchAll(HTML_BLOCK)) {
    const before = content.slice(last, match.index);
    if (before.trim()) parts.push({ type: "markdown", text: before });
    parts.push({ type: "html", html: match[1] });
    last = match.index + match[0].length;
  }
  const rest = content.slice(last);
  if (rest.trim() || parts.length === 0) parts.push({ type: "markdown", text: rest });
  return parts;
}

export function buildMockSrcDoc(html: string) {
  return `<meta http-equiv="Content-Security-Policy" content="${MOCK_CSP}">${html}`;
}
