import { render, screen } from "@testing-library/react";

import type { CosplayerDetail } from "@/lib/types";

import { CosplayerProfile } from "./CosplayerProfile";

const person: CosplayerDetail = {
  id: 1,
  name: "うえ",
  sns_links: ["https://x.com/ue", "javascript:alert(1)", "https://www.instagram.com/ue/"],
  career: "2015年から活動。\n<script>alert(1)</script>",
  description: "日本のコスプレイヤー。",
  notes: "",
  source_url: "https://ja.wikipedia.org/wiki/ue",
  sources: [{ url: "https://ja.wikipedia.org/wiki/ue", fetched_at: "2026-11-19T10:00:00+09:00" }],
};

describe("CosplayerProfile", () => {
  it("安全な SNS だけをリンクにする", () => {
    render(<CosplayerProfile cosplayer={person} />);

    expect(screen.getByRole("heading", { name: "うえ" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "X" })).toHaveAttribute("href", "https://x.com/ue");
    expect(screen.getByRole("link", { name: "Instagram" })).toHaveAttribute("rel", "noopener noreferrer");
    expect(document.querySelector('a[href^="javascript:"]')).toBeNull();
  });

  it("経歴・説明文をテキストとして表示する", () => {
    render(<CosplayerProfile cosplayer={person} />);

    expect(screen.getByText("日本のコスプレイヤー。")).toBeInTheDocument();
    expect(screen.getByText(/<script>alert\(1\)<\/script>/)).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
    expect(screen.getByRole("link", { name: "https://ja.wikipedia.org/wiki/ue" })).toBeInTheDocument();
  });

  it("未登録の項目は「なし」と表示する", () => {
    render(<CosplayerProfile cosplayer={{ ...person, sns_links: [], career: "", notes: "" }} />);

    expect(screen.getAllByText("なし").length).toBe(3);
  });
});
