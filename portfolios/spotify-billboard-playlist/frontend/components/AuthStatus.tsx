import type { Me } from "@/lib/api";

type Props = { me: Me | null; onLogout: () => void };

export default function AuthStatus({ me, onLogout }: Props) {
  if (me === null) {
    return <section className="auth">ログイン状態を確認中…</section>;
  }
  if (!me.authenticated) {
    return (
      <section className="auth">
        <span className="badge off">未ログイン</span>
        {/* OAuth はバックエンドへのページ遷移で開始する */}
        <a className="button spotify" href="/auth/login">
          Spotifyでログイン
        </a>
      </section>
    );
  }
  return (
    <section className="auth">
      <span className="badge on">ログイン中: {me.display_name}</span>
      <button type="button" className="button secondary" onClick={onLogout}>
        ログアウト
      </button>
    </section>
  );
}
