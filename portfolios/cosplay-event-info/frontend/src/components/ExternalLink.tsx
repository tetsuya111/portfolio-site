import type { ReactNode } from "react";

import { safeHttpUrl } from "@/lib/url";

/** http(s) のときだけリンクにする外部リンク（NF-5）。 */
export function ExternalLink({ href, children }: { href: string | null | undefined; children?: ReactNode }) {
  const url = safeHttpUrl(href);
  if (!url) return children ? <span>{children}</span> : null;
  return (
    <a href={url} target="_blank" rel="noopener noreferrer">
      {children ?? url}
    </a>
  );
}
