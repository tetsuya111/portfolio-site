import Link from "next/link";

const STEPS = [
  { icon: "💬", title: "おしゃべりする", text: "「こんなことで困ってる」を、思いつくまま話すだけ。むずかしい言葉はいりません。" },
  { icon: "📝", title: "まとめができる", text: "話した内容をAIが整理。費用の目安も、その場で見られます。" },
  { icon: "📮", title: "送っておしまい", text: "内容を確認して送るだけ。あとはメールでご連絡します。" },
];

export default function LandingPage() {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-10 px-5 py-12">
      <section className="text-center">
        <p className="text-sm font-medium text-amber-700">小さなツールづくりの相談窓口</p>
        <h1 className="mt-3 text-3xl font-bold leading-snug tracking-tight text-stone-900 sm:text-4xl">
          「こんなの、あったらいいな」を
          <br />
          おしゃべりするだけで相談できます
        </h1>
        <p className="mt-4 text-stone-600">
          予約の管理、集計の自動化、ちょっとしたホームページ。
          <br className="hidden sm:inline" />
          業者に頼むほどでもない小さなことこそ、気軽にどうぞ。
        </p>
        <Link
          href="/login"
          className="mt-8 inline-block rounded-full bg-amber-500 px-8 py-3 text-base font-bold text-white shadow-sm transition hover:bg-amber-600"
        >
          無料で相談をはじめる
        </Link>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {STEPS.map((step, index) => (
          <div key={step.title} className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-stone-200">
            <div className="text-3xl">{step.icon}</div>
            <h2 className="mt-3 font-bold text-stone-900">
              {index + 1}. {step.title}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-stone-600">{step.text}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
