import { Suspense } from "react";
import FeedPlayer from "@/components/FeedPlayer";

export default function FeedPage() {
  return (
    <Suspense>
      <FeedPlayer initialContents={[]} totalCount={0} />
    </Suspense>
  );
}
