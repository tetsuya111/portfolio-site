"use client";

export function Modal({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="flex max-h-[85dvh] w-full max-w-lg flex-col gap-4 rounded-3xl bg-white p-6 shadow-xl"
      >
        <h2 className="text-lg font-bold text-stone-900">{title}</h2>
        {children}
      </div>
    </div>
  );
}

export const primaryButton =
  "rounded-full bg-amber-500 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-amber-600 disabled:opacity-50";
export const secondaryButton =
  "rounded-full border border-stone-300 bg-white px-5 py-2.5 text-sm font-medium text-stone-700 transition hover:bg-stone-100 disabled:opacity-50";
