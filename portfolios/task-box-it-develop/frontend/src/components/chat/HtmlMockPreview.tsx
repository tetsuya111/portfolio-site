import { buildMockSrcDoc } from "@/lib/html-mock";

/**
 * 「画面のイメージ」のプレビュー。sandbox を空にしてスクリプトの実行と親ページへのアクセスを禁じ、
 * CSPで外部への通信も禁じる。
 */
export function HtmlMockPreview({ html }: { html: string }) {
  return (
    <figure className="overflow-hidden rounded-xl border border-stone-300 bg-white">
      <figcaption className="border-b border-stone-200 bg-stone-50 px-3 py-1.5 text-xs text-stone-500">
        画面のイメージ（見た目の確認用で、ボタンなどは動きません）
      </figcaption>
      <iframe title="画面のイメージ" sandbox="" srcDoc={buildMockSrcDoc(html)} className="h-96 w-full bg-white" />
    </figure>
  );
}
