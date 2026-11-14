"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api, streamMessage } from "@/lib/api";
import type { AgentCall, ChatMessage, FinalizeResult, PromptTemplate, SummaryDraft, Usage } from "@/lib/types";
import { ActionBar, type ActionKey } from "./ActionBar";
import { Composer } from "./Composer";
import { AgentCallDialog, ClearConfirmDialog, FinalizeDialog, type FinalizeState } from "./dialogs";
import { MessageBubble } from "./MessageBubble";
import { UsageIndicator } from "./UsageIndicator";

const FALLBACK_ERROR = "うまく処理できませんでした。もう一度お試しください。";
const LIMIT_NOTICE = "今日はたくさんお話ししたので、ここまでにさせてください。明日になるとまた使えます。これまでのお話は、このまま読めます。";

type ConversationResponse = { messages: ChatMessage[]; pending_agent_call: AgentCall | null };

export function ChatScreen() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [input, setInput] = useState("");
  const [loaded, setLoaded] = useState(false);
  // 処理中は、入力とすべてのボタンを無効にして、何をしているかを表示する
  const [busy, setBusy] = useState<string | null>(null);
  const [streamingText, setStreamingText] = useState<string | null>(null);
  const [pendingCall, setPendingCall] = useState<AgentCall | null>(null);
  const [finalizeState, setFinalizeState] = useState<FinalizeState | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const [error, setError] = useState("");
  const [usage, setUsage] = useState<Usage | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const refreshUsage = useCallback(() => {
    // 取得に失敗しても対話は続けられるよう、表示を省略するだけにする
    api<{ usage: Usage }>("/me/")
      .then((data) => setUsage(data.usage))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([
      api<ConversationResponse>("/conversation/"),
      api<{ templates: PromptTemplate[] }>("/templates/"),
      api<{ usage: Usage }>("/me/"),
    ])
      .then(([conversation, templateData, me]) => {
        if (!active) return;
        setMessages(conversation.messages);
        setPendingCall(conversation.pending_agent_call);
        setTemplates(templateData.templates);
        setUsage(me.usage);
      })
      .catch((cause) => active && setError(cause instanceof ApiError ? cause.message : FALLBACK_ERROR))
      .finally(() => active && setLoaded(true));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ block: "end" });
  }, [messages, streamingText, busy]);

  const handleError = useCallback((cause: unknown) => {
    if (!(cause instanceof ApiError)) return setError(FALLBACK_ERROR);
    if (cause.code === "daily_limit_reached") {
      // 再取得を待たずに、上限に達した状態を表示に反映する
      return setUsage((current) => ({
        used: current?.used ?? 0,
        limit: current?.limit ?? null,
        limit_reached: true,
        remaining_percent: 0,
        unlimited: false,
      }));
    }
    const missing = cause.data.missing;
    if (cause.code === "summary_incomplete" && Array.isArray(missing) && missing.length > 0) {
      return setFinalizeState({ kind: "missing", missing: missing as string[] });
    }
    setError(cause.message);
  }, []);

  async function run(label: string, task: () => Promise<void>) {
    setBusy(label);
    setError("");
    try {
      await task();
    } catch (cause) {
      handleError(cause);
    } finally {
      setBusy(null);
      refreshUsage();
    }
  }

  function send() {
    const content = input.trim();
    const temp: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      kind: "chat",
      agent_key: "",
      content,
      metadata: {},
      created_at: new Date().toISOString(),
    };
    setMessages((current) => [...current, temp]);
    setInput("");
    setStreamingText("");
    run("考えています…", async () => {
      try {
        await streamMessage(content, ({ event, data }) => {
          if (event === "delta") {
            setStreamingText((text) => (text ?? "") + (data as { text: string }).text);
          } else if (event === "agent_call_request") {
            // 表示中の差分を破棄して、確認ダイアログに切り替える
            setStreamingText(null);
            setPendingCall(data as AgentCall);
          } else if (event === "done") {
            setStreamingText(null);
            setMessages((current) => [...current, (data as { message: ChatMessage }).message]);
          } else if (event === "error") {
            setError((data as { message: string }).message);
          }
        });
      } catch (cause) {
        // サーバーに届いていないので、入力した内容をテキストボックスに戻す
        setMessages((current) => current.filter((message) => message.id !== temp.id));
        setInput(content);
        throw cause;
      } finally {
        setStreamingText(null);
      }
    });
  }

  function answerAgentCall(approve: boolean) {
    const call = pendingCall;
    if (!call) return;
    setPendingCall(null);
    run(approve ? `「${call.agent_name}」を作成しています…（1〜2分かかることがあります）` : "考えています…", async () => {
      const data = await api<{ message: ChatMessage }>(
        `/conversation/agent-calls/${call.id}/${approve ? "approve" : "decline"}/`,
        "POST",
      );
      setMessages((current) => [...current, data.message]);
    });
  }

  function handleAction(key: ActionKey) {
    if (key === "clear") return setConfirmClear(true);
    if (key === "finalize") {
      return run("お話の内容をまとめています…（1〜2分かかることがあります）", async () => {
        const result = await api<FinalizeResult>("/conversation/actions/finalize/", "POST");
        setFinalizeState(
          result.complete ? { kind: "summary", summary: result.summary } : { kind: "missing", missing: result.missing },
        );
      });
    }
    if (key === "summary-download") {
      return run("お話の内容をまとめています…（1〜2分かかることがあります）", async () => {
        const data = await api<{ title: string; body_markdown: string }>(
          "/conversation/actions/summary-download/",
          "POST",
        );
        downloadMarkdown(data.title, data.body_markdown);
      });
    }
    run("見積もりを作成しています…（1〜2分かかることがあります）", async () => {
      const data = await api<{ message: ChatMessage }>(`/conversation/actions/${key}/`, "POST");
      setMessages((current) => [...current, data.message]);
    });
  }

  function submitSummary(summary: SummaryDraft) {
    run("送信しています…", async () => {
      const data = await api<{ notice: string }>(`/summaries/${summary.id}/submit/`, "POST");
      setFinalizeState({ kind: "submitted", notice: data.notice });
    });
  }

  function clearConversation() {
    setConfirmClear(false);
    run("消しています…", async () => {
      await api("/conversation/clear/", "POST");
      setMessages([]);
      setPendingCall(null);
    });
  }

  const limitReached = usage?.limit_reached ?? false;
  const disabled = !loaded || busy !== null || limitReached;

  return (
    <div className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col">
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {loaded && messages.length === 0 && (
          <div className="rounded-2xl bg-white p-5 text-sm leading-relaxed text-stone-600 shadow-sm ring-1 ring-stone-200">
            <p className="font-bold text-stone-900">こんにちは！</p>
            <p className="mt-1">
              「こんなことで困ってる」「こんなのがあったら便利かも」など、思いつくままに話してみてください。
              まとまっていなくて大丈夫です。
            </p>
          </div>
        )}
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {streamingText && (
          <MessageBubble message={{ role: "assistant", kind: "chat", content: streamingText, metadata: {} }} />
        )}
        {busy && !streamingText && (
          <p role="status" className="px-2 text-sm text-stone-500">
            <span className="mr-2 inline-block h-2 w-2 animate-pulse rounded-full bg-amber-500" />
            {busy}
          </p>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="space-y-2 border-t border-stone-200 bg-[#faf7f2] px-4 pb-4 pt-3">
        <UsageIndicator usage={usage} />
        {error && (
          <p role="alert" className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        {limitReached && (
          <p role="status" className="rounded-xl bg-amber-50 px-4 py-2 text-sm text-amber-900">
            {LIMIT_NOTICE}
          </p>
        )}
        <ActionBar disabled={disabled || messages.length === 0} onAction={handleAction} />
        <Composer value={input} onChange={setInput} onSend={send} templates={templates} disabled={disabled} />
      </div>

      {pendingCall && !busy && (
        <AgentCallDialog call={pendingCall} disabled={limitReached} onAnswer={answerAgentCall} />
      )}
      {finalizeState && (
        <FinalizeDialog
          state={finalizeState}
          disabled={busy !== null}
          error={error}
          onSubmit={submitSummary}
          onClose={() => setFinalizeState(null)}
        />
      )}
      {confirmClear && <ClearConfirmDialog onConfirm={clearConversation} onCancel={() => setConfirmClear(false)} />}
    </div>
  );
}

function downloadMarkdown(title: string, body: string) {
  const url = URL.createObjectURL(new Blob([body], { type: "text/markdown;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `${title.replace(/[\\/:*?"<>|]/g, "_") || "要件サマリー"}.md`;
  link.click();
  URL.revokeObjectURL(url);
}
