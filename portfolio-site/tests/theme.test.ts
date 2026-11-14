import { describe, expect, it } from "vitest";
import { DEFAULT_THEME, THEMES, resolveTheme } from "../src/lib/theme";

describe("THEMES", () => {
  it("has minimal and campus, with minimal as the default", () => {
    expect(THEMES).toEqual(["minimal", "campus"]);
    expect(DEFAULT_THEME).toBe("minimal");
  });
});

describe("resolveTheme", () => {
  it("falls back to the default when nothing is set", () => {
    expect(resolveTheme(undefined, undefined)).toBe("minimal");
    expect(resolveTheme("", "  ")).toBe("minimal");
  });

  it("prefers the environment variable over the config file", () => {
    expect(resolveTheme("campus", "minimal")).toBe("campus");
  });

  it("uses the config file when the environment variable is empty", () => {
    expect(resolveTheme("", "campus")).toBe("campus");
    expect(resolveTheme(undefined, "campus")).toBe("campus");
  });

  it("ignores surrounding whitespace", () => {
    expect(resolveTheme(" campus ", undefined)).toBe("campus");
  });

  it.each(["nope", "Campus", "minimal campus"])("rejects unknown theme %j with the valid names", (name) => {
    expect(() => resolveTheme(name, undefined)).toThrow(/minimal, campus/);
  });
});
