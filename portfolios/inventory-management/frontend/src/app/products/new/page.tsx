"use client";

import { useRouter } from "next/navigation";

import { AppShell } from "@/components/AppShell";
import { ProductForm } from "@/components/ProductForm";
import { apiFetch } from "@/lib/api";
import type { Product, ProductInput } from "@/lib/types";

export default function NewProductPage() {
  const router = useRouter();

  async function handleSubmit(values: ProductInput) {
    await apiFetch<Product>("/products", { method: "POST", json: values });
    router.push("/products/");
  }

  return (
    <AppShell title="商品の登録">
      <ProductForm onSubmit={handleSubmit} submitLabel="登録する" />
    </AppShell>
  );
}
