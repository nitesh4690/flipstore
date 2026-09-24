import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import EmptyState from "../../components/EmptyState.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import Pagination from "../../components/Pagination.jsx";
import { useToast } from "../../context/ToastContext.jsx";
import useDocumentTitle from "../../hooks/useDocumentTitle.js";
import { getOrders } from "../../services/shop.js";
import { formatCurrency, formatDate } from "../../utils/format.js";

export function StatusBadge({ status }) {
  const styles = {
    pending: "bg-amber-100 text-amber-700",
    confirmed: "bg-blue-100 text-blue-700",
    processing: "bg-indigo-100 text-indigo-700",
    shipped: "bg-violet-100 text-violet-700",
    delivered: "bg-emerald-100 text-emerald-700",
    cancelled: "bg-red-100 text-red-700",
    paid: "bg-emerald-100 text-emerald-700",
    failed: "bg-red-100 text-red-700",
    refunded: "bg-slate-200 text-slate-600",
  };
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold capitalize ${
        styles[status] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {status}
    </span>
  );
}

/** Order history list with pagination. */
export default function Orders() {
  useDocumentTitle("My orders");
  const toast = useToast();
  const navigate = useNavigate();
  const [data, setData] = useState(null); // null = loading
  const [page, setPage] = useState(1);

  // toast intentionally omitted: the context value is a fresh object per
  // render, and including it would refetch on every render.
  useEffect(() => {
    let cancelled = false;
    getOrders(page)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((error) => {
        if (!cancelled) {
          setData({ items: [], total: 0, page: 1, total_pages: 1 });
          toast.error(error.message || "Could not load orders");
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  if (data === null) return <LoadingSpinner label="Loading orders…" />;

  if (data.items.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <EmptyState
          icon="📦"
          title="No orders yet"
          description="When you place an order it will show up here with live status."
          actionLabel="Start shopping"
          onAction={() => navigate("/products")}
        />
      </div>
    );
  }

  return (
    <section>
      <h2 className="mb-4 text-lg font-bold text-slate-900">Order history</h2>
      <ul className="space-y-3">
        {data.items.map((order) => (
          <li
            key={order.id}
            className="rounded-2xl border border-slate-200 bg-white p-5"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-bold text-slate-900">{order.order_number}</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  Placed {formatDate(order.created_at)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={order.status} />
                <StatusBadge status={order.payment_status} />
              </div>
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3">
              <span className="text-sm text-slate-600">
                Total <strong className="text-slate-900">{formatCurrency(order.total)}</strong>
                {order.discount > 0 && (
                  <span className="ml-1 text-emerald-600">
                    (saved {formatCurrency(order.discount)})
                  </span>
                )}
              </span>
              <Link
                to={`/account/orders/${order.id}`}
                className="rounded-xl bg-slate-900 px-4 py-2 text-xs font-semibold text-white transition hover:bg-slate-700"
              >
                View details
              </Link>
            </div>
          </li>
        ))}
      </ul>

      {data.total_pages > 1 && (
        <div className="mt-6">
          <Pagination page={data.page} totalPages={data.total_pages} onPageChange={setPage} />
        </div>
      )}
    </section>
  );
}
