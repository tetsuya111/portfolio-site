"use client";

import { GoogleLogin } from "@react-oauth/google";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { GOOGLE_CLIENT_ID, useAuth } from "@/components/AuthProvider";

const DEV_LOGIN_ENABLED = process.env.NEXT_PUBLIC_ENABLE_DEV_LOGIN === "true";
const LOGIN_FAILED = "ログインできませんでした。もう一度お試しください。";

export default function LoginPage() {
  const auth = useAuth();
  const router = useRouter();
  const [error, setError] = useState("");

  useEffect(() => {
    if (auth.status === "authenticated") router.replace("/chat");
  }, [auth.status, router]);

  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-6 px-5 py-12">
      <div className="rounded-3xl bg-white p-8 text-center shadow-sm ring-1 ring-stone-200">
        <h1 className="text-xl font-bold text-stone-900">ログイン</h1>
        <p className="mt-2 text-sm text-stone-600">Googleアカウントがあれば、すぐに始められます。</p>
        <div className="mt-6 flex justify-center">
          {GOOGLE_CLIENT_ID ? (
            <GoogleLogin
              onSuccess={(response) => {
                if (!response.credential) return setError(LOGIN_FAILED);
                auth.login(response.credential).catch(() => setError(LOGIN_FAILED));
              }}
              onError={() => setError(LOGIN_FAILED)}
            />
          ) : (
            <p className="text-sm text-red-600">NEXT_PUBLIC_GOOGLE_CLIENT_ID が設定されていません。</p>
          )}
        </div>
        {error && <p role="alert" className="mt-4 text-sm text-red-600">{error}</p>}
        {DEV_LOGIN_ENABLED && (
          <div className="mt-6 space-y-2 border-t border-dashed border-stone-300 pt-4 text-xs text-stone-500">
            <p>開発用ログイン（本番では表示されません）</p>
            <div className="flex justify-center gap-2">
              {[false, true].map((admin) => (
                <button
                  key={String(admin)}
                  type="button"
                  onClick={() => auth.devLogin(admin).catch(() => setError(LOGIN_FAILED))}
                  className="rounded-full border border-stone-300 px-3 py-1.5 hover:bg-stone-100"
                >
                  {admin ? "管理者として入る" : "依頼者として入る"}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
      <ul className="list-disc space-y-1 pl-5 text-xs leading-relaxed text-stone-500">
        <li>お話しした内容は、回答をつくるために外部のAIサービス（Anthropic社のClaude）に送信されます。</li>
        <li>「要件の確定」で送った内容と、Googleアカウントのお名前・メールアドレスは、管理者に届きます。ご連絡はそのメールアドレスにお送りします。</li>
      </ul>
    </div>
  );
}
