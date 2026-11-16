"use client";

// 商品の登録・編集フォーム。

import { useState, type FormEvent } from "react";

import { ApiError } from "@/lib/api";
import type { ProductInput } from "@/lib/types";

interface Props {
  initial?: ProductInput;
  onSubmit: (values: ProductInput) => Promise<void>;
  submitLabel: string;
}

interface FormState {
  sku: string;
  name: string;
  category: string;
  unit: string;
  unit_price: string;
  reorder_point: string;
  description: string;
}

function toState(p?: ProductInput): FormState {
  return {
    sku: p?.sku ?? "",
    name: p?.name ?? "",
    category: p?.category ?? "",
    unit: p?.unit ?? "個",
    unit_price: p?.unit_price == null ? "" : String(p.unit_price),
    reorder_point: String(p?.reorder_point ?? 0),
    description: p?.description ?? "",
  };
}

function toInput(s: FormState): ProductInput {
  const text = (v: string) => (v.trim() === "" ? null : v.trim());
  return {
    sku: s.sku.trim(),
    name: s.name.trim(),
    category: text(s.category),
    unit: s.unit.trim() || "個",
    unit_price: s.unit_price === "" ? null : Number(s.unit_price),
    reorder_point: s.reorder_point === "" ? 0 : Number(s.reorder_point),
    description: text(s.description),
  };
}

export function ProductForm({ initial, onSubmit, submitLabel }: Props) {
  const [state, setState] = useState<FormState>(() => toState(initial));
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const bind = (key: keyof FormState) => ({
    value: state[key],
    onChange: (e: { target: { value: string } }) =>
      setState((prev) => ({ ...prev, [key]: e.target.value })),
  });

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit(toInput(state));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "保存に失敗しました。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="card form" onSubmit={handleSubmit}>
      <div className="form-row">
        <label className="field">
          <span>商品コード</span>
          <input id="sku" required maxLength={50} pattern=".*\S.*" {...bind("sku")} />
        </label>
        <label className="field">
          <span>商品名</span>
          <input id="name" required maxLength={200} pattern=".*\S.*" {...bind("name")} />
        </label>
      </div>
      <div className="form-row">
        <label className="field">
          <span>カテゴリ</span>
          <input maxLength={100} {...bind("category")} />
        </label>
        <label className="field">
          <span>単位</span>
          <input maxLength={20} {...bind("unit")} />
        </label>
      </div>
      <div className="form-row">
        <label className="field">
          <span>単価（円）</span>
          <input type="number" min={0} step={1} inputMode="numeric" {...bind("unit_price")} />
        </label>
        <label className="field">
          <span>発注点</span>
          <input type="number" min={0} step={1} inputMode="numeric" {...bind("reorder_point")} />
        </label>
      </div>
      <label className="field">
        <span>説明</span>
        <textarea rows={3} maxLength={2000} {...bind("description")} />
      </label>
      <p className="muted">在庫数が発注点以下になると「在庫が少ない」と表示します。</p>
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
      <button className="button" type="submit" disabled={submitting}>
        {submitting ? "保存中…" : submitLabel}
      </button>
    </form>
  );
}
