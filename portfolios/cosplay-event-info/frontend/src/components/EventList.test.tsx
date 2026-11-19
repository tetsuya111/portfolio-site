import { render, screen } from "@testing-library/react";

import type { EventSummary } from "@/lib/types";

import { EventList } from "./EventList";

const event: EventSummary = {
  id: 7,
  name: "コスプレフェスタ冬",
  url: "https://official.example/",
  location_raw: "ビッグサイト 西1",
  venue: { id: 1, name: "東京ビッグサイト", prefecture: "東京都", address: "東京都江東区有明3-11-1" },
  start_date: "2026-12-05",
  end_date: "2026-12-06",
  notes: "<b>撮影OK</b>",
  source_url: "https://a.example/1",
};

describe("EventList", () => {
  it("会場名・日付・詳細へのリンクを表示する", () => {
    render(<EventList events={[event]} />);

    // 末尾のスラッシュは next.config の trailingSlash で付く（テスト環境では付かない）
    expect(screen.getByRole("link", { name: "コスプレフェスタ冬" }).getAttribute("href")).toMatch(
      /^\/events\/detail\/?\?id=7$/,
    );
    expect(screen.getByText("2026/12/05 〜 2026/12/06")).toBeInTheDocument();
    expect(screen.getByText("東京ビッグサイト")).toBeInTheDocument();
    expect(screen.getByText("東京都")).toBeInTheDocument();
    // 備考の HTML はタグとして解釈せず文字として表示する
    expect(screen.getByText("<b>撮影OK</b>")).toBeInTheDocument();
  });

  it("会場がなければ取得元の表記を表示する", () => {
    render(<EventList events={[{ ...event, venue: null }]} />);

    expect(screen.getByText("ビッグサイト 西1")).toBeInTheDocument();
  });

  it("0件ならメッセージを表示する", () => {
    render(<EventList events={[]} />);

    expect(screen.getByText("該当するイベントはありません。")).toBeInTheDocument();
  });
});
