import App from "@/components/App";

export default function Home() {
  return (
    <main className="container">
      <h1>Billboard → Spotify Playlist</h1>
      <p className="lead">
        ビルボード・データベースのチャートURLから、Hot 100 の曲を収めた非公開プレイリストを作成します。
      </p>
      <App />
    </main>
  );
}
