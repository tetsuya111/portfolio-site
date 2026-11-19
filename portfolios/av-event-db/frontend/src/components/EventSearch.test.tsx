import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { buildQuery, type SearchQuery } from "@/lib/api";

import { EventDetail } from "./EventDetail";
import { EventSearch } from "./EventSearch";

function page(results: object[], count = results.length, next: string | null = null) {
  return new Response(JSON.stringify({ count, next, previous: null, results }));
}

const item = {
  id: 1,
  title: "発売記念サイン会",
  start_date: "2026-12-03",
  end_date: "2026-12-03",
  start_time: "13:00:00",
  venue: { id: 1, name: "秋葉原ホール", prefecture: "東京都" },
  actresses: ["山田花子", "佐藤美咲"],
};

function calledUrls(fetchMock: ReturnType<typeof vi.fn>) {
  return fetchMock.mock.calls.map((c) => String(c[0]));
}

afterEach(() => vi.unstubAllGlobals());

/** ページ（URL）の代わりに検索条件を持ち、変わったら作り直す。 */
function Harness({ initial, onChange }: { initial: SearchQuery; onChange?: (q: SearchQuery) => void }) {
  const [query, setQuery] = useState(initial);
  return (
    <EventSearch
      key={buildQuery(query).toString()}
      query={query}
      onQueryChange={(q) => {
        onChange?.(q);
        setQuery(q);
      }}
    />
  );
}

describe("EventSearch", () => {
  it("初期条件で検索して一覧を表示する", async () => {
    const fetchMock = vi.fn().mockResolvedValue(page([item]));
    vi.stubGlobal("fetch", fetchMock);
    render(<Harness initial={{ q: "花子" }} />);
    // テスト環境では next.config の trailingSlash が読まれないため、末尾の / は問わない
    expect(await screen.findByRole("link", { name: "発売記念サイン会" })).toHaveAttribute(
      "href",
      expect.stringMatching(/^\/events\/?\?id=1$/),
    );
    expect(screen.getByText("2026/12/03 13:00")).toBeInTheDocument();
    expect(screen.getByText("秋葉原ホール（東京都）")).toBeInTheDocument();
    expect(screen.getByText("出演: 山田花子、佐藤美咲")).toBeInTheDocument();
    expect(screen.getByRole("searchbox")).toHaveValue("花子");
    expect(calledUrls(fetchMock)[0]).toContain("/api/events/?q=%E8%8A%B1%E5%AD%90");
  });

  it("フォーム送信で条件を変えて再検索し、URL 反映用に通知する", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(page([item])));
    vi.stubGlobal("fetch", fetchMock);
    const onChange = vi.fn();
    render(<Harness initial={{}} onChange={onChange} />);
    await screen.findByText("全 1 件");
    await userEvent.type(screen.getByRole("searchbox"), "撮影会");
    await userEvent.selectOptions(screen.getByLabelText("都道府県"), "大阪府");
    await userEvent.click(screen.getByRole("button", { name: "検索" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(calledUrls(fetchMock)[1]).toContain(
      "q=%E6%92%AE%E5%BD%B1%E4%BC%9A&prefecture=%E5%A4%A7%E9%98%AA%E5%BA%9C",
    );
    expect(onChange).toHaveBeenCalledWith({
      q: "撮影会",
      from: "",
      to: "",
      prefecture: "大阪府",
      page: 1,
    });
  });

  it("該当なしのメッセージを出す", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(page([])));
    render(<Harness initial={{}} />);
    expect(await screen.findByText("条件に合うイベントはありません。")).toBeInTheDocument();
  });

  it("次のページへ進む", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(page([item], 25, "http://x/?page=2"))
      .mockResolvedValueOnce(page([{ ...item, id: 2, title: "2ページ目" }], 25));
    vi.stubGlobal("fetch", fetchMock);
    render(<Harness initial={{}} />);
    expect(await screen.findByText("1 / 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "前へ" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "次へ" }));
    expect(await screen.findByText("2ページ目")).toBeInTheDocument();
    expect(calledUrls(fetchMock)[1]).toContain("page=2");
    expect(screen.getByRole("button", { name: "次へ" })).toBeDisabled();
  });

  it("条件（URL）が外から変わったらフォームと結果を合わせる", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(page([item])));
    vi.stubGlobal("fetch", fetchMock);
    const { rerender } = render(
      <EventSearch key="q=foo" query={{ q: "foo" }} onQueryChange={() => {}} />,
    );
    await screen.findByText("全 1 件");
    expect(screen.getByRole("searchbox")).toHaveValue("foo");
    rerender(<EventSearch key="" query={{}} onQueryChange={() => {}} />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(screen.getByRole("searchbox")).toHaveValue("");
    expect(calledUrls(fetchMock)[1]).toMatch(/\/api\/events\/$/);
  });

  it("エラーを表示する", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ from: ["日付は YYYY-MM-DD で指定してください。"] }), {
          status: 400,
        }),
      ),
    );
    render(<Harness initial={{ from: "bad" }} />);
    expect(await screen.findByText("日付は YYYY-MM-DD で指定してください。")).toBeInTheDocument();
  });
});

describe("EventDetail", () => {
  const detail = {
    ...item,
    venue: {
      id: 1,
      name: "秋葉原ホール",
      prefecture: "東京都",
      address: "東京都千代田区",
      latitude: null,
      longitude: null,
    },
    url: "https://shop.example.com/1",
    raw_venue: "秋葉原ホール",
    summary: "<b>概要</b>",
    note: "整理券あり",
    sources: [
      { source_name: "site-a", source_url: "https://a.example.com/1" },
      { source_name: "site-b", source_url: "javascript:alert(1)" },
    ],
  };

  it("全項目と取得元リンクを表示する", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(detail))));
    render(<EventDetail id={1} />);
    expect(await screen.findByRole("heading", { name: "発売記念サイン会" })).toBeInTheDocument();
    expect(screen.getByText("<b>概要</b>")).toBeInTheDocument(); // HTML として解釈しない
    expect(screen.getByText("整理券あり")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "https://shop.example.com/1" })).toHaveAttribute(
      "rel",
      "noopener noreferrer",
    );
    expect(screen.getByRole("link", { name: "Google マップで開く" })).toHaveAttribute(
      "href",
      expect.stringContaining("https://www.google.com/maps/search/"),
    );
    expect(screen.getByRole("link", { name: "site-a: https://a.example.com/1" })).toBeInTheDocument();
    // http(s) 以外の取得元はリンクにしない
    expect(screen.getByText("site-b: javascript:alert(1)").closest("a")).toBeNull();
  });

  it("見つからない場合のメッセージ", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 404 })));
    render(<EventDetail id={9} />);
    expect(await screen.findByText("見つかりませんでした。")).toBeInTheDocument();
  });
});
