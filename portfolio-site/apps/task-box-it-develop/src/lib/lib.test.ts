import { describe, expect, it } from "vitest";
import { buildMockSrcDoc, splitContent } from "./html-mock";
import { createSseParser } from "./sse";

describe("createSseParser", () => {
  it("分割して届いたイベントを、完結した時点で返す", () => {
    const parse = createSseParser();
    expect(parse('event: delta\ndata: {"te')).toEqual([]);
    expect(parse('xt":"こん"}\n\nevent: done\ndata: {"message":1}\n\n')).toEqual([
      { event: "delta", data: { text: "こん" } },
      { event: "done", data: { message: 1 } },
    ]);
  });
});

describe("splitContent", () => {
  it("htmlのコードブロックを画面のイメージとして切り出す", () => {
    const parts = splitContent("こんな感じです\n```html\n<h1>予約</h1>\n```\nどうでしょう");
    expect(parts).toEqual([
      { type: "markdown", text: "こんな感じです\n" },
      { type: "html", html: "<h1>予約</h1>\n" },
      { type: "markdown", text: "\nどうでしょう" },
    ]);
  });

  it("htmlのコードブロックがなければ通常の本文のまま", () => {
    expect(splitContent("```js\nalert(1)\n```")).toEqual([{ type: "markdown", text: "```js\nalert(1)\n```" }]);
    // ストリーミング中で閉じていないブロックは、まだプレビューにしない
    expect(splitContent("```html\n<h1>")).toHaveLength(1);
  });

  it("プレビューの先頭に、外部への通信を禁じるCSPを入れる", () => {
    const srcDoc = buildMockSrcDoc("<img src='https://evil.example/x.png'>");
    expect(srcDoc.startsWith('<meta http-equiv="Content-Security-Policy" content="default-src \'none\';')).toBe(true);
  });
});
