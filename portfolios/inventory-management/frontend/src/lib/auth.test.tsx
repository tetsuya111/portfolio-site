import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getToken, setToken } from "./api";
import { AuthProvider, RequireAuth, useAuth } from "./auth";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: replace }),
}));

const me = { id: 1, username: "alice", role: "staff", is_active: true, created_at: "" };

function stubFetch(responses: Record<string, { status: number; body?: unknown }>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const path = new URL(url).pathname;
      const r = responses[path] ?? { status: 404, body: { detail: "not found" } };
      return new Response(r.body === undefined ? null : JSON.stringify(r.body), {
        status: r.status,
      });
    }),
  );
}

function Who() {
  const { user, signOut } = useAuth();
  return (
    <div>
      <span>user:{user?.username ?? "none"}</span>
      <button onClick={signOut}>logout</button>
    </div>
  );
}

beforeEach(() => replace.mockClear());
afterEach(() => vi.unstubAllGlobals());

describe("AuthProvider", () => {
  it("loads the current user from a stored token", async () => {
    setToken("t");
    stubFetch({ "/users/me": { status: 200, body: me } });
    render(
      <AuthProvider>
        <Who />
      </AuthProvider>,
    );
    expect(await screen.findByText("user:alice")).toBeInTheDocument();
  });

  it("signOut clears token and goes to login", async () => {
    setToken("t");
    stubFetch({ "/users/me": { status: 200, body: me } });
    render(
      <AuthProvider>
        <Who />
      </AuthProvider>,
    );
    await screen.findByText("user:alice");
    await userEvent.click(screen.getByText("logout"));
    expect(getToken()).toBeNull();
    expect(screen.getByText("user:none")).toBeInTheDocument();
    expect(replace).toHaveBeenCalledWith("/login");
  });

  it("drops an invalid token", async () => {
    setToken("expired");
    stubFetch({ "/users/me": { status: 401, body: { detail: "認証が必要です" } } });
    render(
      <AuthProvider>
        <Who />
      </AuthProvider>,
    );
    await waitFor(() => expect(getToken()).toBeNull());
    expect(screen.getByText("user:none")).toBeInTheDocument();
  });
});

describe("RequireAuth", () => {
  it("redirects to login when there is no token", async () => {
    stubFetch({});
    render(
      <AuthProvider>
        <RequireAuth>
          <p>secret</p>
        </RequireAuth>
      </AuthProvider>,
    );
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("renders children for a logged-in user", async () => {
    setToken("t");
    stubFetch({ "/users/me": { status: 200, body: me } });
    render(
      <AuthProvider>
        <RequireAuth>
          <p>secret</p>
        </RequireAuth>
      </AuthProvider>,
    );
    expect(await screen.findByText("secret")).toBeInTheDocument();
  });

  it("shows a message to non-admin users when admin is required", async () => {
    setToken("t");
    stubFetch({ "/users/me": { status: 200, body: me } });
    render(
      <AuthProvider>
        <RequireAuth adminOnly>
          <p>secret</p>
        </RequireAuth>
      </AuthProvider>,
    );
    expect(await screen.findByText("この画面は管理者のみ利用できます。")).toBeInTheDocument();
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });
});
