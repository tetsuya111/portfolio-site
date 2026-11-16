"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { AppShell } from "@/components/AppShell";
import { ApiError, apiFetch, toQuery } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatNumber } from "@/lib/format";
import type { Product } from "@/lib/types";

function ProductList() {
  const { user } = useAuth();
  const [products, setProducts] = useState<Product[] | null>(null);
  const [keyword, setKeyword] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    apiFetch<Product[]>(`/products${toQuery({ q: query })}`)
      .then((items) => {
        if (cancelled) return;
        setProducts(items);
        setError(null);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof ApiError ? e.message : "読み込みに失敗しました。");
      });
    return () => {
      cancelled = true;
    };
  }, [query, reloadKey]);

  function handleSearch(event: FormEvent) {
    event.preventDefault();
    setQuery(keyword.trim());
  }

  async function handleDelete(product: Product) {
    if (!window.confirm(`「${product.name}」を削除しますか？（入出庫履歴は残ります）`)) return;
    try {
      await apiFetch(`/products/${product.id}`, { method: "DELETE" });
      setReloadKey((k) => k + 1);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "削除に失敗しました。");
    }
  }

  return (
    <>
      <form className="toolbar" onSubmit={handleSearch} role="search">
        <label className="field">
          <span>商品コード・商品名で検索</span>
          <input value={keyword} onChange={(e) => setKeyword(e.target.value)} />
        </label>
        <button className="button secondary" type="submit">
          検索
        </button>
        <span className="spacer" />
        <Link className="button" href="/products/new/">
          商品を登録
        </Link>
      </form>
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
      {products === null ? (
        <p className="muted">読み込み中…</p>
      ) : products.length === 0 ? (
        <p className="muted">データがありません。</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>商品コード</th>
                <th>商品名</th>
                <th>カテゴリ</th>
                <th className="num">単価</th>
                <th className="num">在庫数</th>
                <th className="num">発注点</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id}>
                  <td>{p.sku}</td>
                  <td>{p.name}</td>
                  <td>{p.category ?? "—"}</td>
                  <td className="num">{p.unit_price == null ? "—" : `${formatNumber(p.unit_price)}円`}</td>
                  <td className="num">
                    {formatNumber(p.stock)} {p.unit}
                  </td>
                  <td className="num">{formatNumber(p.reorder_point)}</td>
                  <td>
                    <Link className="button secondary small" href={`/products/edit/?id=${p.id}`}>
                      編集
                    </Link>{" "}
                    {user?.role === "admin" && (
                      <button
                        type="button"
                        className="button danger small"
                        onClick={() => handleDelete(p)}
                      >
                        削除
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

export default function ProductsPage() {
  return (
    <AppShell title="商品">
      <ProductList />
    </AppShell>
  );
}
