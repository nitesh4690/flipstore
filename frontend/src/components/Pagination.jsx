/**
 * Page navigation with a compact numeric window.
 * Calls onPageChange(page) and scrolls the window to top.
 */
export default function Pagination({ page, totalPages, onPageChange }) {
  if (!totalPages || totalPages <= 1) return null;

  const go = (next) => {
    if (next < 1 || next > totalPages || next === page) return;
    onPageChange(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // Window of page numbers around the current page, with ellipses.
  const pages = [];
  const push = (value) => pages.push(value);
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i += 1) push(i);
  } else {
    push(1);
    if (page > 3) push("…");
    for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i += 1) push(i);
    if (page < totalPages - 2) push("…");
    push(totalPages);
  }

  const base =
    "min-h-10 min-w-10 rounded-xl px-3 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <nav aria-label="Pagination" className="mt-10 flex flex-wrap items-center justify-center gap-2">
      <button
        type="button"
        onClick={() => go(page - 1)}
        disabled={page <= 1}
        className={`${base} border border-slate-300 bg-white text-slate-600 hover:bg-slate-50`}
      >
        ← Prev
      </button>
      {pages.map((entry, index) =>
        entry === "…" ? (
          <span key={`gap-${index}`} className="px-2 text-slate-400">
            …
          </span>
        ) : (
          <button
            key={entry}
            type="button"
            aria-current={entry === page ? "page" : undefined}
            onClick={() => go(entry)}
            className={`${base} ${
              entry === page
                ? "bg-brand-600 text-white shadow"
                : "border border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
            }`}
          >
            {entry}
          </button>
        ),
      )}
      <button
        type="button"
        onClick={() => go(page + 1)}
        disabled={page >= totalPages}
        className={`${base} border border-slate-300 bg-white text-slate-600 hover:bg-slate-50`}
      >
        Next →
      </button>
    </nav>
  );
}
