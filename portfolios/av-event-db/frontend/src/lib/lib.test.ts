import { ApiError, buildQuery, fetchEvents, fetchMapVenues, parseQuery } from "./api";
import { addDays, formatPeriod, mapsSearchUrl, safeExternalUrl, toIsoDate } from "./format";

describe("safeExternalUrl", () => {
  it("http(s) だけを許可する", () => {
    expect(safeExternalUrl("https://example.com/a")).toBe("https://example.com/a");
    expect(safeExternalUrl("http://example.com/")).toBe("http://example.com/");
    expect(safeExternalUrl("javascript:alert(1)")).toBeNull();
    expect(safeExternalUrl("data:text/html,x")).toBeNull();
    expect(safeExternalUrl("/relative")).toBeNull();
    expect(safeExternalUrl("")).toBeNull();
  });
});

describe("format", () => {
  it("Google マップの検索リンクを作る", () => {
    expect(mapsSearchUrl("秋葉原 ホール", "東京都")).toBe(
      "https://www.google.com/maps/search/?api=1&query=%E7%A7%8B%E8%91%89%E5%8E%9F%20%E3%83%9B%E3%83%BC%E3%83%AB%20%E6%9D%B1%E4%BA%AC%E9%83%BD",
    );
  });

  it("開催期間を表示用にする", () => {
    expect(formatPeriod("2026-12-03", "2026-12-03", "13:00:00")).toBe("2026/12/03 13:00");
    expect(formatPeriod("2026-12-03", "2026-12-05", null)).toBe("2026/12/03〜2026/12/05");
  });

  it("日付を YYYY-MM-DD にする", () => {
    expect(toIsoDate(addDays(new Date(2026, 11, 30), 3))).toBe("2027-01-02");
  });
});

describe("api", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("空の条件を省いてクエリを作る", () => {
    expect(buildQuery({ q: " 花子 ", from: "", prefecture: "東京都", page: 1 }).toString()).toBe(
      "q=%E8%8A%B1%E5%AD%90&prefecture=%E6%9D%B1%E4%BA%AC%E9%83%BD",
    );
    expect(buildQuery({ page: 3 }).toString()).toBe("page=3");
  });

  it("URL のクエリから検索条件を読む", () => {
    expect(parseQuery(new URLSearchParams("q=a&page=2"))).toEqual({
      q: "a",
      from: "",
      to: "",
      prefecture: "",
      page: 2,
    });
    expect(parseQuery(new URLSearchParams("page=x")).page).toBe(1);
  });

  it("イベント一覧 API を呼ぶ", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ count: 0, next: null, previous: null, results: [] })),
    );
    vi.stubGlobal("fetch", fetchMock);
    await fetchEvents({ q: "x", page: 2 });
    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/api/events/?q=x&page=2");
  });

  it("400 のメッセージを ApiError にする", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ to: ["終了日は開始日以降にしてください。"] }), { status: 400 }),
      ),
    );
    await expect(fetchMapVenues("2026-12-05", "2026-12-01")).rejects.toEqual(
      new ApiError("終了日は開始日以降にしてください。", 400),
    );
  });

  it("通信エラーを ApiError にする", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("failed")));
    await expect(fetchEvents({})).rejects.toBeInstanceOf(ApiError);
  });
});
