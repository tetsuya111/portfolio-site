export type User = {
  id: number;
  email: string;
  display_name: string;
  role: "general" | "admin";
};

export type Usage = {
  used: number;
  // 管理者は上限がないため limit / remaining_percent は null になる
  limit: number | null;
  limit_reached: boolean;
  remaining_percent: number | null;
  unlimited: boolean;
};

export type MessageMetadata = {
  agent_name?: string;
  is_estimate?: boolean;
  is_preview?: boolean;
  completed_items?: string[];
  title?: string;
};

export type ChatMessage = {
  id: number | string;
  role: "user" | "assistant";
  kind: "chat" | "agent_result";
  agent_key: string;
  content: string;
  metadata: MessageMetadata;
  created_at: string;
};

export type AgentCall = { id: number; agent_key: string; agent_name: string };

export type PromptTemplate = { id: number; label: string; prompt: string };

export type SummaryDraft = { id: number; title: string; body_markdown: string };

export type FinalizeResult =
  | { complete: false; missing: string[] }
  | { complete: true; summary: SummaryDraft };

export type HandlingStatus = "new" | "in_progress" | "done";

export const HANDLING_STATUS_LABELS: Record<HandlingStatus, string> = {
  new: "未対応",
  in_progress: "対応中",
  done: "対応済み",
};

export type AdminSummary = {
  id: number;
  title: string;
  user_name: string;
  submitted_at: string;
  handling_status: HandlingStatus;
  mail_status: "pending" | "sent" | "failed";
};

export type AdminSummaryDetail = AdminSummary & {
  user_email: string;
  body_markdown: string;
  mail_error: string;
};
