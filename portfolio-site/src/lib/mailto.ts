// コンタクトフォームの mailto: リンクを作る。ブラウザで動く送信処理（ConsultCta.astro）から読み込むため、依存を持たない。

/**
 * フォームの各項目の最大文字数（入力欄の maxlength に使う）。
 * 日本語は1文字が URL エンコードで9文字になり、Windows のメールソフトなどは約 2,048 文字を超える mailto: を
 * 開けないため、すべて上限まで日本語で埋めてもリンクが 2,000 文字に収まる値にしている（tests/consultation.test.ts）。
 */
export const MAILTO_LIMITS = { name: 30, email: 100, message: 120 } as const;

/** フォームの入力から、宛先・件名・本文を埋めた mailto: リンクを作る。値はすべて URL エンコードする。 */
export function buildMailto(to: string, input: { name: string; email: string; message: string }): string {
  const subject = "【ご相談】ポートフォリオサイトから";
  const body = [`お名前: ${input.name}`, `返信先メールアドレス: ${input.email}`, "", "ご相談内容:", input.message]
    .join("\n")
    .replace(/\r?\n/g, "\r\n");
  return `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}
