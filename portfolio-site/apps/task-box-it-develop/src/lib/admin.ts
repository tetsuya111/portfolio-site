import type { HandlingStatus } from "./types";

export function formatDateTime(value: string) {
  return new Date(value).toLocaleString("ja-JP", { dateStyle: "medium", timeStyle: "short" });
}

export const STATUS_STYLES: Record<HandlingStatus, string> = {
  new: "bg-red-100 text-red-800",
  in_progress: "bg-amber-100 text-amber-800",
  done: "bg-stone-200 text-stone-600",
};
