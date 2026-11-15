// コンタクトフォームの mailto: リンクを作る。ブラウザで動く送信処理（ConsultCta.astro）から読み込むため、依存を持たない。

/** フォームの入力から、宛先・件名・本文を埋めた mailto: リンクを作る。値はすべて URL エンコードする。 */
export function buildMailto(to: string, input: { name: string; email: string; message: string }): string {
  const subject = `【ご相談】${input.name} さまより`;
  const body = [`お名前: ${input.name}`, `返信先メールアドレス: ${input.email}`, "", "ご相談内容:", input.message]
    .join("\n")
    .replace(/\r?\n/g, "\r\n");
  return `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}
