"use client";

import { useCallback, useEffect, useState } from "react";
import AuthStatus from "@/components/AuthStatus";
import PlaylistForm from "@/components/PlaylistForm";
import * as api from "@/lib/api";

export default function App() {
  const [me, setMe] = useState<api.Me | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshMe = useCallback(async () => {
    try {
      setMe(await api.getMe());
      setError(null);
    } catch (e) {
      setMe({ authenticated: false });
      setError(e instanceof api.ApiError ? e.message : "ログイン状態を取得できませんでした");
    }
  }, []);

  useEffect(() => {
    // マウント時に一度だけログイン状態を取得する（外部APIとの同期）
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshMe();
  }, [refreshMe]);

  async function handleLogout() {
    try {
      await api.logout();
    } finally {
      await refreshMe();
    }
  }

  return (
    <>
      <AuthStatus me={me} onLogout={handleLogout} />
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <PlaylistForm authenticated={me?.authenticated ?? false} onUnauthorized={refreshMe} />
    </>
  );
}
