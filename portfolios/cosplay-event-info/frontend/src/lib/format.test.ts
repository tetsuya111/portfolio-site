import { addDays, formatDate, formatDateRange, toIsoDate } from "./format";

describe("日付の表示", () => {
  it("1日だけのイベント", () => {
    expect(formatDateRange("2026-12-05", "2026-12-05")).toBe("2026/12/05");
  });

  it("複数日のイベント", () => {
    expect(formatDateRange("2026-12-05", "2026-12-06")).toBe("2026/12/05 〜 2026/12/06");
  });

  it("formatDate", () => {
    expect(formatDate("2027-01-02")).toBe("2027/01/02");
  });
});

describe("日付の計算", () => {
  it("ローカル日付を YYYY-MM-DD にする", () => {
    expect(toIsoDate(new Date(2026, 0, 9))).toBe("2026-01-09");
  });

  it("月・年をまたいで日数を足す", () => {
    expect(addDays("2026-12-20", 30)).toBe("2027-01-19");
  });
});
