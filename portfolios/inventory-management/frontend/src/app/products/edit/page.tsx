"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { ProductForm } from "@/components/ProductForm";
import { ApiError, apiFetch } from "@/lib/api";
import type { Product, ProductInput } from "@/lib/types";

function EditProduct() {
  const router = useRouter();
  const id = Number(useSearchParams().get("id"));
  const validId = Number.isInteger(id) && id > 0;
  const [product, setProduct] = useState<Product | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!validId) return;
    apiFetch<Product>(`/products/${id}`)
      .then(setProduct)
      .catch((e) => setError(e instanceof ApiError ? e.message : "読み込みに失敗しました。"));
  }, [id, validId]);

  async function handleSubmit(values: ProductInput) {
    await apiFetch<Product>(`/products/${id}`, { method: "PUT", json: values });
    router.push("/products/");
  }

  if (!validId) return <p className="alert">商品が指定されていません。</p>;
  if (error) return <p className="alert">{error}</p>;
  if (!product) return <p className="muted">読み込み中…</p>;
  return (
    <>
      <p className="muted">
        現在の在庫数: {product.stock} {product.unit}（在庫数は入出庫の登録でのみ変わります）
      </p>
      <ProductForm initial={product} onSubmit={handleSubmit} submitLabel="更新する" />
    </>
  );
}

export default function EditProductPage() {
  return (
    <AppShell title="商品の編集">
      <Suspense fallback={<p className="muted">読み込み中…</p>}>
        <EditProduct />
      </Suspense>
    </AppShell>
  );
}
