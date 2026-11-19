type Props = {
  page: number;
  count: number;
  pageSize?: number;
  onChange: (page: number) => void;
};

export function Pagination({ page, count, pageSize = 20, onChange }: Props) {
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  if (totalPages <= 1) return null;
  return (
    <nav className="pagination" aria-label="ページ送り">
      <button type="button" className="secondary" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        前へ
      </button>
      <span>
        {page} / {totalPages} ページ
      </span>
      <button
        type="button"
        className="secondary"
        disabled={page >= totalPages}
        onClick={() => onChange(page + 1)}
      >
        次へ
      </button>
    </nav>
  );
}
