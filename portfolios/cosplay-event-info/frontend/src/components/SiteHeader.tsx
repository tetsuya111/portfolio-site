import Link from "next/link";

const NAV = [
  { href: "/events/", label: "イベント" },
  { href: "/map/", label: "地図" },
  { href: "/cosplayers/", label: "コスプレイヤー" },
];

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="container site-header-inner">
        <Link href="/" className="site-title">
          コスプレイベント情報まとめ
        </Link>
        <nav aria-label="メインメニュー">
          <ul className="nav-list">
            {NAV.map((item) => (
              <li key={item.href}>
                <Link href={item.href}>{item.label}</Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </header>
  );
}
