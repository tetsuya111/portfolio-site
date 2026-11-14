import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import App from "@/components/App";
import * as api from "@/lib/api";

const me: api.Me = { authenticated: true, id: "u1", display_name: "Tetsu", csrf_token: "tok" };

describe("App", () => {
  it("loads the login state on mount", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(me);
    render(<App />);
    expect(await screen.findByText(/ログイン中: Tetsu/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "プレイリストを作成" })).toBeEnabled();
  });

  it("logs out and refreshes the state", async () => {
    vi.spyOn(api, "getMe").mockResolvedValueOnce(me).mockResolvedValueOnce({ authenticated: false });
    const logout = vi.spyOn(api, "logout").mockResolvedValue();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "ログアウト" }));
    expect(logout).toHaveBeenCalledOnce();
    expect(await screen.findByRole("link", { name: "Spotifyでログイン" })).toBeInTheDocument();
  });

  it("shows an error when logout fails", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(me);
    vi.spyOn(api, "logout").mockRejectedValue(new api.ApiError(0, "サーバーに接続できませんでした"));
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "ログアウト" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("サーバーに接続できませんでした");
  });
});
