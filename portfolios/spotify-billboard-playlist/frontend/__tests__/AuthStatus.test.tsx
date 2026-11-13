import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import AuthStatus from "@/components/AuthStatus";

describe("AuthStatus", () => {
  it("shows a login link when unauthenticated", () => {
    render(<AuthStatus me={{ authenticated: false }} onLogout={() => {}} />);
    const link = screen.getByRole("link", { name: "Spotifyでログイン" });
    expect(link).toHaveAttribute("href", "/auth/login");
    expect(screen.getByText("未ログイン")).toBeInTheDocument();
  });

  it("shows the display name and logout button when authenticated", async () => {
    const onLogout = vi.fn();
    render(
      <AuthStatus me={{ authenticated: true, id: "u1", display_name: "Tetsu" }} onLogout={onLogout} />,
    );
    expect(screen.getByText(/ログイン中: Tetsu/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Spotifyでログイン" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "ログアウト" }));
    expect(onLogout).toHaveBeenCalledOnce();
  });

  it("shows loading while me is unknown", () => {
    render(<AuthStatus me={null} onLogout={() => {}} />);
    expect(screen.getByText("ログイン状態を確認中…")).toBeInTheDocument();
  });
});
