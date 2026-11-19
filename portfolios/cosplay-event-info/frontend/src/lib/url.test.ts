import { googleMapsEmbedUrl, googleMapsSearchUrl, safeHttpUrl, snsLabel, venueQuery } from "./url";

describe("safeHttpUrl", () => {
  it.each([
    ["javascript:alert(1)", null],
    ["data:text/html,x", null],
    ["/relative", null],
    ["", null],
    [null, null],
    [undefined, null],
    ["https://example.com/a?b=1", "https://example.com/a?b=1"],
    ["http://example.com/", "http://example.com/"],
  ])("%s → %s", (input, expected) => {
    expect(safeHttpUrl(input)).toBe(expected);
  });
});

describe("Google マップの URL", () => {
  it("埋め込み URL に output=embed とエンコードした検索語を含む", () => {
    const url = googleMapsEmbedUrl("東京ビッグサイト 東京都江東区有明3-11-1");

    expect(url.startsWith("https://www.google.com/maps?")).toBe(true);
    expect(url).toContain("output=embed");
    expect(url).toContain(`q=${encodeURIComponent("東京ビッグサイト 東京都江東区有明3-11-1")}`);
  });

  it("検索 URL は Maps URLs 形式", () => {
    expect(googleMapsSearchUrl("幕張メッセ&A")).toBe(
      "https://www.google.com/maps/search/?api=1&query=%E5%B9%95%E5%BC%B5%E3%83%A1%E3%83%83%E3%82%BB%26A",
    );
  });

  it("会場があれば会場名と住所、なければ取得元の表記で検索する", () => {
    expect(venueQuery({ id: 1, name: "幕張メッセ", prefecture: "千葉県", address: "千葉県千葉市" }, "メッセ")).toBe(
      "幕張メッセ 千葉県千葉市",
    );
    expect(venueQuery(null, "どこかのホール")).toBe("どこかのホール");
  });
});

describe("snsLabel", () => {
  it.each([
    ["https://x.com/a", "X"],
    ["https://twitter.com/a", "X"],
    ["https://www.instagram.com/a/", "Instagram"],
    ["https://www.youtube.com/@a", "YouTube"],
    ["https://www.tiktok.com/@a", "TikTok"],
    ["https://example.com/a", "example.com"],
  ])("%s → %s", (url, label) => {
    expect(snsLabel(url)).toBe(label);
  });
});
