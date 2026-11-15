import { describe, expect, it } from "vitest";
import { articleSchema, isLinkTarget, portfolioSchema, profileSchema, serviceSchema, skillSchema } from "../src/lib/schemas";

describe("profileSchema", () => {
  it("requires name and role", () => {
    expect(profileSchema.safeParse({ role: "Engineer" }).success).toBe(false);
    expect(profileSchema.safeParse({ name: "Taro" }).success).toBe(false);
    expect(profileSchema.safeParse({ name: "Taro", role: "Engineer" }).success).toBe(true);
  });

  it("rejects non-http links", () => {
    const r = profileSchema.safeParse({
      name: "Taro",
      role: "Engineer",
      links: [{ label: "x", url: "javascript:alert(1)" }],
    });
    expect(r.success).toBe(false);
  });

  it("rejects site-relative links", () => {
    const r = profileSchema.safeParse({ name: "Taro", role: "Engineer", links: [{ label: "x", url: "/apps/x/" }] });
    expect(r.success).toBe(false);
  });
});

describe("portfolioSchema", () => {
  it("defaults tags to an empty array", () => {
    expect(portfolioSchema.parse({ title: "App" }).tags).toEqual([]);
  });

  it("rejects a javascript: url", () => {
    expect(portfolioSchema.safeParse({ title: "App", url: "javascript:alert(1)" }).success).toBe(false);
  });

  it("accepts an https url", () => {
    expect(portfolioSchema.parse({ title: "App", url: "https://example.com" }).url).toBe(
      "https://example.com",
    );
  });

  it("accepts a site-relative path", () => {
    expect(portfolioSchema.parse({ title: "App", url: "/apps/my-app/" }).url).toBe("/apps/my-app/");
  });

  it.each(["//evil.com/", "/\\evil.com/", "/a b", "/a\\b", "/a\nb", "/a\tb", "/a\u0085b", "/a\u200bb", "/a\ufeffb", "/a\u202eb", "/a\u00adb", "/a\u2066b", "apps/x/", ""])(
    "rejects an unsafe or non-root path %j",
    (url) => {
      expect(portfolioSchema.safeParse({ title: "App", url }).success).toBe(false);
    },
  );

  it("explains the accepted url forms when invalid", () => {
    const r = portfolioSchema.safeParse({ title: "App", url: "ftp://x" });
    expect(r.success).toBe(false);
    expect(r.error?.issues[0]?.message).toContain("/ で始まるサイト内のパス");
  });

  it("requires title", () => {
    expect(portfolioSchema.safeParse({ tags: ["a"] }).success).toBe(false);
  });
});

describe("articleSchema", () => {
  it("rejects an impossible date", () => {
    expect(articleSchema.safeParse({ title: "a", date: "2026-13-40" }).success).toBe(false);
  });

  it("requires date", () => {
    expect(articleSchema.safeParse({ title: "a" }).success).toBe(false);
  });

  it("defaults draft to false and coerces date", () => {
    const a = articleSchema.parse({ title: "a", date: "2026-11-13" });
    expect(a.draft).toBe(false);
    expect(a.date).toBeInstanceOf(Date);
    expect(a.tags).toEqual([]);
  });
});

describe("portfolioSchema description", () => {
  it("accepts an optional description", () => {
    expect(portfolioSchema.parse({ title: "t", description: "概要" }).description).toBe("概要");
    expect(portfolioSchema.parse({ title: "t" }).description).toBeUndefined();
  });
});

describe("serviceSchema", () => {
  it("requires title and description and defaults order to 0", () => {
    expect(serviceSchema.parse({ title: "t", description: "d" }).order).toBe(0);
    expect(serviceSchema.safeParse({ title: "t" }).success).toBe(false);
    expect(serviceSchema.safeParse({ description: "d" }).success).toBe(false);
  });
});

describe("skillSchema", () => {
  it("defaults examples, famous and order", () => {
    const s = skillSchema.parse({ name: "Python", category: "言語", description: "d" });
    expect(s.examples).toEqual([]);
    expect(s.famous).toEqual([]);
    expect(s.order).toBe(0);
  });

  it("requires name, category and description", () => {
    expect(skillSchema.safeParse({ category: "c", description: "d" }).success).toBe(false);
    expect(skillSchema.safeParse({ name: "n", description: "d" }).success).toBe(false);
    expect(skillSchema.safeParse({ name: "n", category: "c" }).success).toBe(false);
  });
});

describe("isLinkTarget", () => {
  it("accepts http(s) urls and site paths", () => {
    expect(isLinkTarget("/apps/x/")).toBe(true);
    expect(isLinkTarget("https://a.example")).toBe(true);
  });

  it("rejects script urls and other hosts written as paths", () => {
    expect(isLinkTarget("javascript:alert(1)")).toBe(false);
    expect(isLinkTarget("//evil.example")).toBe(false);
    expect(isLinkTarget("")).toBe(false);
  });
});
