import { describe, expect, it } from "vitest";
import { buildArticleMarkdown } from "../src/admin/admin-client";
import { parseMarkdown } from "../src/lib/markdown-file";
import { articleSchema } from "../src/lib/schemas";

describe("buildArticleMarkdown", () => {
  it("produces frontmatter that passes the article schema even with YAML-special characters", () => {
    const md = buildArticleMarkdown({
      title: 'タイトル: "引用" # と --- を含む',
      date: "2026-11-13",
      tags: ["a: b", "c"],
      description: "",
      draft: true,
      body: "本文",
    });
    const { data, body } = parseMarkdown(md);
    const parsed = articleSchema.parse(data);
    expect(parsed.title).toBe('タイトル: "引用" # と --- を含む');
    expect(parsed.tags).toEqual(["a: b", "c"]);
    expect(parsed.draft).toBe(true);
    expect(data).not.toHaveProperty("description");
    expect(body).toBe("\n本文\n");
  });
});
