import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import PlaylistForm, { playlistName } from "@/components/PlaylistForm";
import * as api from "@/lib/api";

const chart: api.Chart = {
  id: 1,
  url: "https://billboard.mryogaku.com/php/chart.php?date=2025-11-15",
  title: "ビルボード Hot 100 全順位（2025年11月15日付）",
  tracks: [
    { rank: 1, title: "The Fate Of Ophelia", artist: "Taylor Swift" },
    { rank: 2, title: "Golden", artist: "HUNTR/X" },
  ],
};

const result: api.PlaylistResult = {
  playlist_id: "pl1",
  url: "https://open.spotify.com/playlist/pl1",
  added: 95,
  not_found: [{ title: "Golden", artist: "HUNTR/X" }],
};

describe("PlaylistForm", () => {
  it("disabled_when_unauthenticated", () => {
    render(<PlaylistForm authenticated={false} />);
    expect(screen.getByRole("button", { name: "プレイリストを作成" })).toBeDisabled();
    expect(screen.getByLabelText("チャートURL")).toHaveValue("https://billboard.mryogaku.com/");
  });

  it("creates_playlist_and_shows_result", async () => {
    const fetchChart = vi.spyOn(api, "fetchChart").mockResolvedValue(chart);
    const createPlaylist = vi.spyOn(api, "createPlaylist").mockResolvedValue(result);
    render(<PlaylistForm authenticated />);

    const input = screen.getByLabelText("チャートURL");
    await userEvent.clear(input);
    await userEvent.type(input, chart.url);
    await userEvent.click(screen.getByRole("button", { name: "プレイリストを作成" }));

    expect(fetchChart).toHaveBeenCalledWith(chart.url);
    expect(createPlaylist).toHaveBeenCalledWith("ビルボード Hot 100 全順位-2025/11/15", [
      { title: "The Fate Of Ophelia", artist: "Taylor Swift" },
      { title: "Golden", artist: "HUNTR/X" },
    ]);
    const link = await screen.findByRole("link", { name: /Spotifyで開く/ });
    expect(link).toHaveAttribute("href", result.url);
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
    expect(screen.getByText(/95曲/)).toBeInTheDocument();
    expect(screen.getByText("Golden / HUNTR/X")).toBeInTheDocument();
  });

  it("uses_default_name_when_backend_returns_no_title", async () => {
    // 古いバックエンドは title を返さない。その場合も既定の名前で作成できること
    const { title: _omit, ...withoutTitle } = chart;
    vi.spyOn(api, "fetchChart").mockResolvedValue(withoutTitle as api.Chart);
    const createPlaylist = vi.spyOn(api, "createPlaylist").mockResolvedValue(result);
    render(<PlaylistForm authenticated />);
    await userEvent.clear(screen.getByLabelText("チャートURL"));
    await userEvent.type(screen.getByLabelText("チャートURL"), chart.url);
    await userEvent.click(screen.getByRole("button", { name: "プレイリストを作成" }));
    expect(await screen.findByRole("link", { name: /Spotifyで開く/ })).toBeInTheDocument();
    expect(createPlaylist.mock.calls[0][0]).toBe("ビルボード Hot 100-2025/11/15");
  });

  it("sends_only_first_100_tracks_and_notes_it", async () => {
    const many: api.Chart = {
      ...chart,
      tracks: Array.from({ length: 150 }, (_, i) => ({ rank: i + 1, title: `T${i + 1}`, artist: "A" })),
    };
    vi.spyOn(api, "fetchChart").mockResolvedValue(many);
    const createPlaylist = vi.spyOn(api, "createPlaylist").mockResolvedValue(result);
    render(<PlaylistForm authenticated />);
    await userEvent.click(screen.getByRole("button", { name: "プレイリストを作成" }));

    await screen.findByRole("link", { name: /Spotifyで開く/ });
    const sent = createPlaylist.mock.calls[0][1];
    expect(sent).toHaveLength(100);
    expect(sent[99]).toEqual({ title: "T100", artist: "A" });
    expect(screen.getByText(/150曲.*先頭の100曲/)).toBeInTheDocument();
  });

  it("shows_backend_error_detail", async () => {
    vi.spyOn(api, "fetchChart").mockRejectedValue(
      new api.ApiError(400, "billboard.mryogaku.com のURLのみ指定できます"),
    );
    const createPlaylist = vi.spyOn(api, "createPlaylist");
    render(<PlaylistForm authenticated />);
    await userEvent.click(screen.getByRole("button", { name: "プレイリストを作成" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "billboard.mryogaku.com のURLのみ指定できます",
    );
    expect(createPlaylist).not.toHaveBeenCalled();
  });

  it("notifies_on_unauthorized", async () => {
    vi.spyOn(api, "fetchChart").mockResolvedValue(chart);
    vi.spyOn(api, "createPlaylist").mockRejectedValue(new api.ApiError(401, "再ログインしてください"));
    const onUnauthorized = vi.fn();
    render(<PlaylistForm authenticated onUnauthorized={onUnauthorized} />);
    await userEvent.click(screen.getByRole("button", { name: "プレイリストを作成" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("再ログインしてください");
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it("disabled_while_loading", async () => {
    let resolve: (c: api.Chart) => void = () => {};
    vi.spyOn(api, "fetchChart").mockReturnValue(new Promise((r) => (resolve = r)));
    vi.spyOn(api, "createPlaylist").mockResolvedValue(result);
    render(<PlaylistForm authenticated />);
    await userEvent.click(screen.getByRole("button", { name: "プレイリストを作成" }));
    const button = screen.getByRole("button", { name: "作成中…" });
    expect(button).toBeDisabled();
    resolve(chart);
    expect(await screen.findByRole("link", { name: /Spotifyで開く/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "プレイリストを作成" })).toBeEnabled();
  });

  it("requires_a_url", async () => {
    const fetchChart = vi.spyOn(api, "fetchChart");
    render(<PlaylistForm authenticated />);
    await userEvent.clear(screen.getByLabelText("チャートURL"));
    await userEvent.click(screen.getByRole("button", { name: "プレイリストを作成" }));
    expect(fetchChart).not.toHaveBeenCalled();
  });
});

describe("playlistName", () => {
  it("uses the page title and the date query parameter", () => {
    expect(playlistName("https://billboard.mryogaku.com/php/chart.php?date=2025-11-15", "Hot 100 全順位")).toBe(
      "Hot 100 全順位-2025/11/15",
    );
  });

  it("uses the page title with today's date when the url has no date", () => {
    expect(
      playlistName("https://billboard.mryogaku.com/php/alltime.php?page=1", "歴代ランキング", new Date(2026, 10, 13)),
    ).toBe("歴代ランキング-2026/11/13");
  });

  it("removes date notations from the page title", () => {
    const url = "https://x/?date=2025-11-15";
    expect(playlistName(url, "ビルボード Hot 100 全順位（2025年11月15日付）")).toBe("ビルボード Hot 100 全順位-2025/11/15");
    expect(playlistName(url, "Hot 100 (2025年1月5日) 全順位")).toBe("Hot 100 全順位-2025/11/15");
    expect(playlistName(url, "2025/11/15 付 Hot 100")).toBe("Hot 100-2025/11/15");
    expect(playlistName(url, "Hot 100 2025-11-15")).toBe("Hot 100-2025/11/15");
    expect(playlistName(url, "歴代 1〜20位（オールタイム）")).toBe("歴代 1〜20位（オールタイム）-2025/11/15");
  });

  it("falls back to the default title when only a date remains", () => {
    expect(playlistName("https://x/?date=2025-11-15", "（2025年11月15日付）")).toBe("ビルボード Hot 100-2025/11/15");
  });

  it("falls back to the default title when the page has none", () => {
    expect(playlistName("https://billboard.mryogaku.com/", "  ", new Date(2026, 10, 13))).toBe(
      "ビルボード Hot 100-2026/11/13",
    );
  });

  it("shortens a long title so the name fits in 100 characters", () => {
    const name = playlistName("https://x/?date=2025-11-15", "あ".repeat(150));
    expect(Array.from(name)).toHaveLength(100);
    expect(name.endsWith("-2025/11/15")).toBe(true);
  });

  it("ignores a malformed date", () => {
    expect(playlistName("https://x/?date=<script>", "", new Date(2026, 0, 2))).toBe(
      "ビルボード Hot 100-2026/01/02",
    );
  });

  it("tolerates an unparsable url", () => {
    expect(playlistName("not a url", "", new Date(2026, 0, 2))).toBe("ビルボード Hot 100-2026/01/02");
  });
});
