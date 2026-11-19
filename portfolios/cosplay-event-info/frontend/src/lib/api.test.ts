import { ApiError, fetchCosplayer, fetchEvents, fetchVenues } from "./api";

function mockFetch(body: unknown, status = 200) {
  const fn = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }),
  );
  vi.stubGlobal("fetch", fn);
  return fn;
}

const emptyPage = { count: 0, next: null, previous: null, results: [] };

describe("fetchEvents", () => {
  it("空の条件はクエリに含めない", async () => {
    const fn = mockFetch(emptyPage);

    await fetchEvents({ q: "コスプレ", from: "", to: "2026-12-31", prefecture: undefined, page: 2 });

    const url = new URL(fn.mock.calls[0][0] as string);
    expect(url.pathname).toBe("/api/events/");
    expect(Object.fromEntries(url.searchParams)).toEqual({ q: "コスプレ", to: "2026-12-31", page: "2" });
  });

  it("エラー時は ApiError（メッセージは API の内容）", async () => {
    mockFetch({ from: ["日付は YYYY-MM-DD 形式で指定してください。"] }, 400);

    const error = await fetchEvents({ from: "x" }).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(400);
    expect((error as ApiError).message).toContain("YYYY-MM-DD");
  });

  it("通信失敗も ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(fetchEvents({})).rejects.toBeInstanceOf(ApiError);
  });
});

describe("その他の API", () => {
  it("fetchVenues は期間をクエリに付ける", async () => {
    const fn = mockFetch([]);

    await fetchVenues("2026-12-01", "2026-12-31");

    const url = new URL(fn.mock.calls[0][0] as string);
    expect(url.pathname).toBe("/api/venues/");
    expect(url.searchParams.get("from")).toBe("2026-12-01");
    expect(url.searchParams.get("to")).toBe("2026-12-31");
  });

  it("fetchCosplayer は id のパスを呼ぶ", async () => {
    const fn = mockFetch({ id: 3 });

    await fetchCosplayer(3);

    expect(new URL(fn.mock.calls[0][0] as string).pathname).toBe("/api/cosplayers/3/");
  });
});
