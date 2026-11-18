// バックエンド（backend/app/schemas.py）の入出力に対応する型。

export type Role = "admin" | "staff" | "visitor";
export type MovementType = "in" | "out";

/** 1回の入出庫の数量の上限（backend/app/schemas.py の MAX_QUANTITY と同じ値）。 */
export const MAX_QUANTITY = 1_000_000;

export interface User {
  id: number;
  username: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface Product {
  id: number;
  sku: string;
  name: string;
  category: string | null;
  unit: string;
  unit_price: number | null;
  reorder_point: number;
  stock: number;
  description: string | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductInput {
  sku: string;
  name: string;
  category: string | null;
  unit: string;
  unit_price: number | null;
  reorder_point: number;
  description: string | null;
}

export interface Movement {
  id: number;
  product_id: number;
  product_sku: string;
  product_name: string;
  type: MovementType;
  quantity: number;
  stock_after: number;
  note: string | null;
  user_id: number;
  username: string;
  created_at: string;
}

export interface HistoryPage {
  items: Movement[];
  total: number;
  limit: number;
  offset: number;
}

export interface SummaryItem {
  product_id: number;
  sku: string;
  name: string;
  unit: string;
  stock: number;
  reorder_point: number;
  is_low: boolean;
}

export interface Summary {
  items: SummaryItem[];
  total_products: number;
  total_stock: number;
  low_stock_count: number;
}
