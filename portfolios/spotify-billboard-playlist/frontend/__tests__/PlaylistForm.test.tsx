import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import PlaylistForm, { playlistName } from "@/components/PlaylistForm";
import * as api from "@/lib/api";

const chart: api.Chart = {
  id: 1,
  url: "https://billboard.mryogaku.com/php/chart.php?date=2025-11-15",
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
    expect(createPlaylist).toHaveBeenCalledWith("Billboard Hot 100 (2025-11-15)", [
      { title: "The Fate Of Ophelia", artist: "Taylor Swift" },
      { title: "Golden", artist: "HUNTR/X" },
    ]);
    const link = await screen.findByRole("link", { name: /Spotifyで開く/ });
    expect(link).toHaveAttribute("href", result.url);
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
    expect(screen.getByText(/95曲/)).toBeInTheDocument();
    expect(screen.getByText("Golden / HUNTR/X")).toBeInTheDocument();
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
  it("uses the date query parameter", () => {
    expect(playlistName("https://billboard.mryogaku.com/php/chart.php?date=2025-11-15")).toBe(
      "Billboard Hot 100 (2025-11-15)",
    );
  });

  it("falls back to today's date", () => {
    expect(playlistName("https://billboard.mryogaku.com/", new Date(2026, 10, 13))).toBe(
      "Billboard Hot 100 (2026-11-13)",
    );
  });

  it("ignores a malformed date", () => {
    expect(playlistName("https://x/?date=<script>", new Date(2026, 0, 2))).toBe(
      "Billboard Hot 100 (2026-01-02)",
    );
  });

  it("tolerates an unparsable url", () => {
    expect(playlistName("not a url", new Date(2026, 0, 2))).toBe("Billboard Hot 100 (2026-01-02)");
  });
});
