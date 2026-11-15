import { describe, expect, it } from "vitest";
import { buildMailto, resolveConsultation } from "../src/lib/consultation";

const MOCK = { taskBoxMockUrl: "/apps/task-box-it-develop/" };

describe("resolveConsultation contactEmail", () => {
  it("uses a valid address", () => {
    expect(resolveConsultation({ contactEmail: "me@example.com" }, MOCK).contactEmail).toBe("me@example.com");
  });

  it.each([undefined, "", "  ", "not-an-email", "a@b.com?bcc=x@y.com", "a@b.com&cc=x@y.com"])(
    "treats %j as unset",
    (contactEmail) => {
      expect(resolveConsultation({ contactEmail }, MOCK).contactEmail).toBeNull();
    },
  );
});

describe("resolveConsultation taskBox", () => {
  it("prefers the env url and opens external urls in a new tab", () => {
    expect(resolveConsultation({ taskBoxUrl: "https://task.example/" }, MOCK).taskBox).toEqual({
      href: "https://task.example/",
      external: true,
    });
  });

  it.each([undefined, "", "javascript:alert(1)", "//evil.example"])("falls back to the mock for %j", (taskBoxUrl) => {
    expect(resolveConsultation({ taskBoxUrl }, MOCK).taskBox).toEqual({
      href: "/apps/task-box-it-develop/",
      external: false,
    });
  });

  it("returns null when neither is usable", () => {
    expect(resolveConsultation({}, {}).taskBox).toBeNull();
    expect(resolveConsultation({ taskBoxUrl: "javascript:x" }, { taskBoxMockUrl: "javascript:y" }).taskBox).toBeNull();
  });
});

describe("buildMailto", () => {
  it("puts the form values into the subject and body", () => {
    const url = buildMailto("to@example.com", { name: "山田 & 太郎", email: "y@example.com", message: "1行目\n#2行目" });
    const m = /^mailto:to@example\.com\?subject=([^&]*)&body=([^&]*)$/.exec(url);
    expect(m).not.toBeNull();
    expect(decodeURIComponent(m?.[1] ?? "")).toBe("【ご相談】山田 & 太郎 さまより");
    const body = decodeURIComponent(m?.[2] ?? "");
    expect(body).toContain("お名前: 山田 & 太郎");
    expect(body).toContain("返信先メールアドレス: y@example.com");
    expect(body).toContain("1行目\r\n#2行目");
  });
});
