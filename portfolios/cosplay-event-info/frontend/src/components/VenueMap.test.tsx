import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { VenueWithEvents } from "@/lib/types";
import { googleMapsEmbedUrl } from "@/lib/url";

import { VenueMap } from "./VenueMap";

const venues: VenueWithEvents[] = [
  {
    id: 1,
    name: "東京ビッグサイト",
    prefecture: "東京都",
    address: "東京都江東区有明3-11-1",
    event_count: 2,
    events: [
      { id: 10, name: "冬フェス", start_date: "2026-12-05", end_date: "2026-12-06" },
      { id: 11, name: "新春撮影会", start_date: "2027-01-03", end_date: "2027-01-03" },
    ],
  },
  {
    id: 2,
    name: "インテックス大阪",
    prefecture: "大阪府",
    address: "",
    event_count: 1,
    events: [{ id: 12, name: "なにわ祭", start_date: "2026-12-12", end_date: "2026-12-12" }],
  },
];

describe("VenueMap", () => {
  it("会場一覧を件数付きで表示し、最初の会場の地図を出す", () => {
    render(<VenueMap venues={venues} />);

    expect(screen.getByRole("button", { name: /東京ビッグサイト.*2 件/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /インテックス大阪.*1 件/ })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByTitle("東京ビッグサイトの地図")).toHaveAttribute(
      "src",
      googleMapsEmbedUrl("東京ビッグサイト 東京都江東区有明3-11-1"),
    );
    expect(screen.getByRole("link", { name: "冬フェス" })).toBeInTheDocument();
  });

  it("会場を選ぶとその会場の地図とイベントを表示する", async () => {
    const user = userEvent.setup();
    render(<VenueMap venues={venues} />);

    await user.click(screen.getByRole("button", { name: /インテックス大阪/ }));

    expect(screen.getByTitle("インテックス大阪の地図")).toHaveAttribute(
      "src",
      googleMapsEmbedUrl("インテックス大阪"),
    );
    expect(screen.getByRole("link", { name: "なにわ祭" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "冬フェス" })).not.toBeInTheDocument();
  });

  it("会場がなければメッセージを表示する", () => {
    render(<VenueMap venues={[]} />);

    expect(screen.getByText("この期間に開催されるイベントはありません。")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
