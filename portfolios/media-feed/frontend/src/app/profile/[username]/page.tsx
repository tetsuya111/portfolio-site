import ProfilePageClient from "@/components/ProfilePageClient";

// 静的出力（output: "export"）では動的ルートのページを事前に作る必要がある。
// ポートフォリオのモック（handlers.js）が返すデモ用の値だけを出力する。
export function generateStaticParams() { return [{ username: "demo" }]; }

export default async function ProfilePage({ params }: { params: Promise<{ username: string }> }) {
  const { username } = await params;
  return <ProfilePageClient username={username} />;
}
