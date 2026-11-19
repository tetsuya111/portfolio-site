import Link from "next/link";

import type { Cosplayer } from "@/lib/types";

const SUMMARY_LENGTH = 80;

export function CosplayerList({ cosplayers }: { cosplayers: Cosplayer[] }) {
  if (cosplayers.length === 0) {
    return <p className="muted">該当するコスプレイヤーはいません。</p>;
  }
  return (
    <ul className="card-list">
      {cosplayers.map((person) => (
        <li key={person.id} className="card">
          <p className="card-title">
            <Link href={`/cosplayers/detail/?id=${person.id}`}>{person.name}</Link>
          </p>
          {person.description && (
            <p className="muted" style={{ margin: 0 }}>
              {person.description.length > SUMMARY_LENGTH
                ? `${person.description.slice(0, SUMMARY_LENGTH)}…`
                : person.description}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}
