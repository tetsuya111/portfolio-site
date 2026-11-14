import { describe, expect, it } from "vitest";
import { articleSchema, portfolioSchema, profileSchema } from "../src/lib/schemas";

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

  it.each(["//evil.com/", "/\\evil.com/", "/a b", "/a\\b", "/a\nb", "/a\tb", "apps/x/", ""])(
    "rejects an unsafe or non-root path %j",
    (url) => {
      expect(portfolioSchema.safeParse({ title: "App", url }).success).toBe(false);
    },
  );

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
