import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { MapsApi } from "@/lib/googleMaps";

import { EventMap } from "./EventMap";

const TODAY = new Date(2026, 11, 1);

const venues = [
  {
    id: 1,
    name: "秋葉原ホール",
    address: "東京都千代田区",
    prefecture: "東京都",
    latitude: 35.7,
    longitude: 139.77,
    events: [
      { id: 10, title: "サイン会", start_date: "2026-12-03", end_date: "2026-12-03", start_time: null },
    ],
  },
  {
    id: 2,
    name: "博多ショップ",
    address: "",
    prefecture: "福岡県",
    latitude: null,
    longitude: null,
    events: [
      { id: 11, title: "握手会", start_date: "2026-12-05", end_date: "2026-12-05", start_time: null },
    ],
  },
];

function stubVenues(body: unknown = venues) {
  const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(body))));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function fakeMaps() {
  const markers: { title: string; click?: () => void }[] = [];
  // new で呼ばれるため、アロー関数ではなくクラスで用意する
  const api = {
    Map: class {
      fitBounds = vi.fn();
      setCenter = vi.fn();
      setZoom = vi.fn();
    },
    Marker: class {
      private m: { title: string; click?: () => void };
      constructor(opts: { title: string }) {
        this.m = { title: opts.title };
        markers.push(this.m);
      }
      addListener(_: string, handler: () => void) {
        this.m.click = handler;
      }
      setMap = vi.fn();
    },
    LatLngBounds: class {
      extend = vi.fn();
    },
  };
  return { api: api as unknown as MapsApi, markers };
}

afterEach(() => vi.unstubAllGlobals());

describe("EventMap", () => {
  it("既定で今日から30日間の会場を取得する", async () => {
    const fetchMock = stubVenues();
    render(<EventMap today={TODAY} />);
    await screen.findByText("会場一覧");
    expect(String(fetchMock.mock.calls[0][0])).toContain("from=2026-12-01&to=2026-12-31");
  });

  it("APIキー未設定なら全会場を Google マップのリンク付きで一覧表示する", async () => {
    stubVenues();
    render(<EventMap today={TODAY} />);
    expect(await screen.findByText("秋葉原ホール")).toBeInTheDocument();
    expect(screen.getByText("博多ショップ")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Google マップで開く" })).toHaveLength(2);
    expect(screen.queryByRole("region", { name: "会場の地図" })).not.toBeInTheDocument();
  });

  it("期間を変えると再取得する", async () => {
    const fetchMock = stubVenues();
    render(<EventMap today={TODAY} />);
    await screen.findByText("会場一覧");
    const from = screen.getByLabelText("開始日");
    await userEvent.clear(from);
    await userEvent.type(from, "2026-12-10");
    await userEvent.click(screen.getByRole("button", { name: "表示" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(String(fetchMock.mock.calls[1][0])).toContain("from=2026-12-10");
  });

  it("期間内のイベントがなければメッセージを出す", async () => {
    stubVenues([]);
    render(<EventMap today={TODAY} />);
    expect(await screen.findByText("期間内に開催されるイベントはありません。")).toBeInTheDocument();
  });

  it("APIキーがあれば座標のある会場をピン表示し、座標のない会場は一覧に出す", async () => {
    stubVenues();
    const { api, markers } = fakeMaps();
    const loadMaps = vi.fn().mockResolvedValue(api);
    render(<EventMap apiKey="KEY" today={TODAY} loadMaps={loadMaps} />);
    expect(await screen.findByText("地図に表示できない会場")).toBeInTheDocument();
    await waitFor(() => expect(markers).toHaveLength(1));
    expect(loadMaps).toHaveBeenCalledWith("KEY");
    expect(markers[0].title).toBe("秋葉原ホール");
    expect(screen.getByText("博多ショップ")).toBeInTheDocument();
    expect(screen.queryByText("サイン会")).not.toBeInTheDocument();

    // ピンを選ぶと会場のイベント一覧を出す
    markers[0].click?.();
    expect(await screen.findByText("選択した会場")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "サイン会" })).toBeInTheDocument();
  });

  it("地図を読み込めなければ一覧に切り替える", async () => {
    stubVenues();
    render(<EventMap apiKey="KEY" today={TODAY} loadMaps={() => Promise.reject(new Error("x"))} />);
    expect(await screen.findByText(/地図を読み込めませんでした/)).toBeInTheDocument();
    expect(screen.getByText("会場一覧")).toBeInTheDocument();
    expect(screen.getByText("秋葉原ホール")).toBeInTheDocument();
  });
});
