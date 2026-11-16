"use client";

import { useEffect, useState, type FormEvent } from "react";

import { AppShell } from "@/components/AppShell";
import { ApiError, apiFetch, movementPath } from "@/lib/api";
import { formatNumber, movementTypeLabel } from "@/lib/format";
import { MAX_QUANTITY, type Movement, type MovementType, type Product } from "@/lib/types";

function RecordForm() {
  const [products, setProducts] = useState<Product[] | null>(null);
  const [type, setType] = useState<MovementType>("in");
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Movement | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  // 登録のたび（成功・失敗とも）に読み直し、他の利用者の入出庫を在庫数の表示に反映する。
  useEffect(() => {
    apiFetch<Product[]>("/products")
      .then(setProducts)
      .catch((e) => setError(e instanceof ApiError ? e.message : "読み込みに失敗しました。"));
  }, [reloadKey]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setResult(null);
    setSubmitting(true);
    try {
      const movement = await apiFetch<Movement>(movementPath(type), {
        method: "POST",
        json: { product_id: Number(productId), quantity: Number(quantity), note: note.trim() || null },
      });
      setResult(movement);
      setQuantity("1");
      setNote("");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "登録に失敗しました。");
    } finally {
      setSubmitting(false);
      setReloadKey((k) => k + 1);
    }
  }

  if (products === null && !error) return <p className="muted">読み込み中…</p>;
  if (products?.length === 0) return <p className="muted">商品が登録されていません。先に商品を登録してください。</p>;

  return (
    <form className="card form" onSubmit={handleSubmit}>
      <div className="segmented" role="group" aria-label="区分">
        {(["in", "out"] as const).map((t) => (
          <button key={t} type="button" aria-pressed={type === t} onClick={() => setType(t)}>
            {movementTypeLabel(t)}
          </button>
        ))}
      </div>
      <label className="field">
        <span>商品</span>
        <select value={productId} onChange={(e) => setProductId(e.target.value)} required>
          <option value="">選択してください</option>
          {products?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.sku} {p.name}（在庫 {formatNumber(p.stock)} {p.unit}）
            </option>
          ))}
        </select>
      </label>
      <div className="form-row">
        <label className="field">
          <span>数量</span>
          <input
            type="number"
            min={1}
            max={MAX_QUANTITY}
            step={1}
            inputMode="numeric"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            required
          />
        </label>
        <label className="field">
          <span>備考（任意）</span>
          <input maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
      </div>
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
      {result && (
        <p className="notice" role="status">
          {result.product_name} を {formatNumber(result.quantity)} {movementTypeLabel(result.type)}
          しました。現在の在庫数: {formatNumber(result.stock_after)}
        </p>
      )}
      <button className="button" type="submit" disabled={submitting}>
        {submitting ? "登録中…" : `${movementTypeLabel(type)}を登録`}
      </button>
    </form>
  );
}

export default function RecordPage() {
  return (
    <AppShell title="入出庫の登録">
      <RecordForm />
    </AppShell>
  );
}
