import { describe, expect, it } from "vitest";
import { assertValidSlug, isValidSlug } from "../src/lib/slug";
import { ContentValidationError } from "../src/lib/errors";

describe("isValidSlug", () => {
  it.each(["my-app", "a1", "a".repeat(64)])("accepts %s", (s) => {
    expect(isValidSlug(s)).toBe(true);
  });

  it.each(["", "a".repeat(65), "My-App", "../x", "a/b", "a--b", "-a", "a-", "あ", "a b"])(
    "rejects %j",
    (s) => {
      expect(isValidSlug(s)).toBe(false);
    },
  );
});

describe("assertValidSlug", () => {
  it("throws ContentValidationError for a path-like slug", () => {
    expect(() => assertValidSlug("../x")).toThrow(ContentValidationError);
  });

  it("does not throw for a valid slug", () => {
    expect(() => assertValidSlug("hello-world")).not.toThrow();
  });
});
