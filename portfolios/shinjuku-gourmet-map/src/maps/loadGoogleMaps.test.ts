import { afterEach, describe, expect, test, vi } from "vitest";
import { CALLBACK_NAME, LOAD_TIMEOUT_MS, loadGoogleMaps, SCRIPT_ID } from "./loadGoogleMaps";

type TestWindow = Window & Record<string, unknown>;
const win = window as unknown as TestWindow;

function findScript(): HTMLScriptElement {
  const script = document.getElementById(SCRIPT_ID);
  if (!(script instanceof HTMLScriptElement)) throw new Error("script がない");
  return script;
}

/** Google の読み込み完了を模倣する */
function simulateLoaded(importLibrary = vi.fn(async (name: string) => ({ name }))) {
  win.google = { maps: { importLibrary } };
  (win[CALLBACK_NAME] as () => void)();
  return importLibrary;
}

afterEach(() => {
  vi.useRealTimers();
  document.getElementById(SCRIPT_ID)?.remove();
  delete win.google;
  delete win[CALLBACK_NAME];
  delete win.gm_authFailure;
});

describe("loadGoogleMaps", () => {
  test("APIキー・言語・地域・コールバック付きの script を追加する", () => {
    void loadGoogleMaps({ apiKey: "k&ey" });
    const url = new URL(findScript().src);
    expect(url.origin + url.pathname).toBe("https://maps.googleapis.com/maps/api/js");
    expect(url.searchParams.get("key")).toBe("k&ey");
    expect(url.searchParams.get("loading")).toBe("async");
    expect(url.searchParams.get("language")).toBe("ja");
    expect(url.searchParams.get("region")).toBe("JP");
    expect(url.searchParams.get("callback")).toBe(CALLBACK_NAME);
    expect(findScript().async).toBe(true);
  });

  test("読み込み完了で4つのライブラリを返す", async () => {
    const promise = loadGoogleMaps({ apiKey: "k" });
    const importLibrary = simulateLoaded();
    const libs = await promise;
    expect(importLibrary.mock.calls.map((c) => c[0]).sort()).toEqual(["core", "maps", "marker", "places"]);
    expect(libs.places).toEqual({ name: "places" });
  });

  test("script の読み込みに失敗したら reject する", async () => {
    const promise = loadGoogleMaps({ apiKey: "k" });
    findScript().dispatchEvent(new Event("error"));
    await expect(promise).rejects.toThrow("Google マップを読み込めませんでした");
  });

  test("一定時間内に読み込みが終わらなければ reject する", async () => {
    vi.useFakeTimers();
    const promise = loadGoogleMaps({ apiKey: "k" });
    const assertion = expect(promise).rejects.toThrow("時間内に");
    await vi.advanceTimersByTimeAsync(LOAD_TIMEOUT_MS);
    await assertion;
  });

  test("認証に失敗したら onAuthFailure を呼ぶ", () => {
    const onAuthFailure = vi.fn();
    void loadGoogleMaps({ apiKey: "k", onAuthFailure });
    (win.gm_authFailure as () => void)();
    expect(onAuthFailure).toHaveBeenCalledOnce();
  });
});
