"use client";

import { EventMap } from "@/components/EventMap";

export default function MapPage() {
  return (
    <>
      <h1>地図で探す</h1>
      <EventMap apiKey={process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || undefined} />
    </>
  );
}
