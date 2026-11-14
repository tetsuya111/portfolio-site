"use client";

import { RequireAuth } from "@/components/AuthProvider";
import { ChatScreen } from "@/components/chat/ChatScreen";

export default function ChatPage() {
  return (
    <RequireAuth>
      <ChatScreen />
    </RequireAuth>
  );
}
