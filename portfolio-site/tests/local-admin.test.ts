import { Readable } from "node:stream";
import type { IncomingMessage } from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { describe, expect, it, vi } from "vitest";
import { BodyTooLargeError, CONTENT_ROOT_DEFINE, localAdmin, readBodyWithLimit } from "../integrations/local-admin";

type SetupOptions = Parameters<NonNullable<ReturnType<typeof localAdmin>["hooks"]["astro:config:setup"]>>[0];

function runConfigSetup(command: "dev" | "build" | "preview" | "sync") {
  const injectRoute = vi.fn();
  const updateConfig = vi.fn();
  const hook = localAdmin({ contentRoot: "./content" }).hooks["astro:config:setup"];
  if (!hook) throw new Error("astro:config:setup がありません");
  const config = { root: pathToFileURL(join(tmpdir(), "site") + "/") };
  hook({ command, injectRoute, updateConfig, config } as unknown as SetupOptions);
  return { injectRoute, updateConfig };
}

describe("localAdmin", () => {
  it("injects admin routes in dev", () => {
    const { injectRoute } = runConfigSetup("dev");
    expect(injectRoute.mock.calls.map((c) => c[0].pattern)).toEqual([
      "/admin",
      "/admin/profile",
      "/admin/articles/new",
    ]);
  });

  it("exposes the resolved content root to admin pages in dev", () => {
    const { updateConfig } = runConfigSetup("dev");
    expect(updateConfig).toHaveBeenCalledWith({
      vite: { define: { [CONTENT_ROOT_DEFINE]: JSON.stringify(join(tmpdir(), "site", "content")) } },
    });
  });

  it.each(["build", "preview", "sync"] as const)("injects nothing for %s", (command) => {
    const { injectRoute, updateConfig } = runConfigSetup(command);
    expect(injectRoute).not.toHaveBeenCalled();
    expect(updateConfig).not.toHaveBeenCalled();
  });
});

const stream = (chunks: string[]) => Readable.from(chunks.map((c) => Buffer.from(c))) as unknown as IncomingMessage;

describe("readBodyWithLimit", () => {
  it("returns the body within the limit", async () => {
    expect(await readBodyWithLimit(stream(["ab", "cd"]), 4)).toBe("abcd");
  });

  it("throws when the body exceeds the limit", async () => {
    await expect(readBodyWithLimit(stream(["ab", "cde"]), 4)).rejects.toThrow(BodyTooLargeError);
  });

  it("decodes multi-byte characters split across chunks", async () => {
    const bytes = Buffer.from("日本");
    const s = Readable.from([bytes.subarray(0, 2), bytes.subarray(2)]) as unknown as IncomingMessage;
    expect(await readBodyWithLimit(s, 100)).toBe("日本");
  });
});
