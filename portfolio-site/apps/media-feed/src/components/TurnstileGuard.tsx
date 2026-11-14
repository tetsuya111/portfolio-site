"use client";

import { useState, useEffect } from "react";
import { isTurnstileVerified } from "@/lib/auth";
import TurnstileDialog from "@/components/TurnstileDialog";

const TURNSTILE_ENABLED = process.env.NEXT_PUBLIC_TURNSTILE_ENABLED !== "false";

export default function TurnstileGuard() {
  const [verified, setVerified] = useState(false);

  useEffect(() => {
    if (!TURNSTILE_ENABLED) return;
    setVerified(isTurnstileVerified());
  }, []);

  if (!TURNSTILE_ENABLED || verified) return null;
  return <TurnstileDialog onVerified={() => setVerified(true)} />;
}
