"use client";

import { useEffect, useState, type FormEvent } from "react";

import { AppShell } from "@/components/AppShell";
import { ApiError, apiFetch } from "@/lib/api";
import { ROLE_LABEL, formatDateTime } from "@/lib/format";
import type { Role, User } from "@/lib/types";

function Users() {
  const [users, setUsers] = useState<User[] | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("staff");
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiFetch<User[]>("/users")
      .then((items) => {
        if (cancelled) return;
        setUsers(items);
        setLoadError(null);
      })
      .catch((e) => {
        if (!cancelled) setLoadError(e instanceof ApiError ? e.message : "読み込みに失敗しました。");
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setSubmitting(true);
    try {
      const created = await apiFetch<User>("/auth/register", {
        method: "POST",
        json: { username: username.trim(), password, role },
      });
      setNotice(`${created.username}（${ROLE_LABEL[created.role]}）を登録しました。`);
      setUsername("");
      setPassword("");
      setRole("staff");
      setReloadKey((k) => k + 1);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "登録に失敗しました。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid cols-2">
      <section>
        <h2>登録済みのユーザー</h2>
        {loadError ? (
          <p className="alert">{loadError}</p>
        ) : users === null ? (
          <p className="muted">読み込み中…</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ユーザー名</th>
                  <th>権限</th>
                  <th>作成日時</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>
                      {u.username}
                      {!u.is_active && <span className="muted">（無効）</span>}
                    </td>
                    <td>{ROLE_LABEL[u.role]}</td>
                    <td>{formatDateTime(u.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <section>
        <h2>ユーザーの登録</h2>
        <form className="card" onSubmit={handleSubmit}>
          <label className="field">
            <span>ユーザー名（3〜50文字の英数字・_・-）</span>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              minLength={3}
              maxLength={50}
              pattern="[A-Za-z0-9_\-]+"
              autoComplete="off"
              required
            />
          </label>
          <label className="field">
            <span>パスワード（8文字以上）</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              autoComplete="new-password"
              required
            />
          </label>
          <label className="field">
            <span>権限</span>
            <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
              <option value="staff">一般（商品の削除・ユーザー登録以外）</option>
              <option value="admin">管理者（すべての操作）</option>
              <option value="visitor">閲覧者（閲覧のみ）</option>
            </select>
          </label>
          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}
          {notice && (
            <p className="notice" role="status">
              {notice}
            </p>
          )}
          <button className="button" type="submit" disabled={submitting}>
            {submitting ? "登録中…" : "登録する"}
          </button>
        </form>
      </section>
    </div>
  );
}

export default function UsersPage() {
  return (
    <AppShell title="ユーザー管理" adminOnly>
      <Users />
    </AppShell>
  );
}
