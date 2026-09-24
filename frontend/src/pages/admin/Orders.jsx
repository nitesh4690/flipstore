import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import EmptyState from "../../components/EmptyState.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import Pagination from "../../components/Pagination.jsx";
import { StatusBadge } from "../account/Orders.jsx";
import { useToast } from "../../context/ToastContext.jsx";
import useDocumentTitle from "../../hooks/useDocumentTitle.js";
import { getAdminOrders } from "../../services/admin.js";
import { formatCurrency, formatDate } from "../../utils/format.js";

const STATUSES = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"];

/** All-orders table with status filter + search (URL-driven). */
export default function AdminOrders() {
  useDocumentTitle("Admin · Orders");
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState(null);

  const status = searchParams.get("status") || "";
  const search = searchParams.get("search") || "";
  const page = Number(searchParams.get("page")) || 1;
  const [searchInput, setSearchInput] = useState(search);

  const setParam = (updates) => {
    const next = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value === "" || value === null) next.delete(key);
      else next.set(key, String(value));
    });
    setSearchParams(next);
  };

  // toast intentionally omitted from deps (fresh object per render).
  useEffect(() => {
    let cancelled = false;
    getAdminOrders({ status, search, page, limit: 10 })
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((error) => {
        if (!cancelled) toast.error(error.message || "Could not load orders");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, search, page]);

  if (!data) return <LoadingSpinner label="Loading orders…" />;

  const statusTabs = [{ id: "", label: "All" }, ...STATUSES.map((id) => ({
    id,
    label: id[0].toUpperCase() + id.slice(1),
  }))];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900">Orders</h1>
        <p className="text-sm text-slate-500">{data.total} orders total</p>
      </div>

      {/* Status filter tabs */}
      <div className="flex flex-wrap gap-2">
        {statusTabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setParam({ status: tab.id, page: 1 })}
            className={`rounded-full px-3.5 py-1.5 text-sm font-semibold transition ${
              status === tab.id
                ? "bg-slate-900 text-white"
                : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Search */}
      <form
        className="flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          setParam({ search: searchInput.trim(), page: 1 });
        }}
      >
        <input
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Search order # or customer email…"
          className="h-11 w-full max-w-sm rounded-xl border border-slate-300 px-3 text-sm outline-none transition focus:border-brand-500"
        />
        <button
          type="submit"
          className="h-11 rounded-xl bg-slate-900 px-4 text-sm font-semibold text-white transition hover:bg-slate-700"
        >
          Search
        </button>
        {(status || search) && (
          <button
            type="button"
            onClick={() => {
              setSearchInput("");
              setSearchParams({});
            }}
            className="h-11 rounded-xl border border-slate-300 px-4 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
          >
            Reset
          </button>
        )}
      </form>

      {data.items.length === 0 ? (
        <EmptyState
          icon="🧾"
          title="No orders found"
          description={
            status || search
              ? "Try clearing the filters."
              : "Orders appear here as customers check out."
          }
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Order</th>
                  <th className="px-4 py-3">Customer</th>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Payment</th>
                  <th className="px-4 py-3 text-right">Total</th>
                  <th className="px-4 py-3 text-right">View</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((order) => (
                  <tr key={order.id} className="transition hover:bg-slate-50">
                    <td className="px-4 py-3 font-semibold text-slate-900">{order.order_number}</td>
                    <td className="max-w-52 truncate px-4 py-3 text-slate-600">
                      {order.customer?.email}
                      <span className="block text-xs text-slate-400">
                        {order.customer?.first_name} {order.customer?.last_name}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-500">{formatDate(order.created_at)}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={order.status} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={order.payment_status} />
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-slate-900">
                      {formatCurrency(order.total)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/admin/orders/${order.id}`}
                        className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-slate-700"
                      >
                        Manage
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <Pagination page={data.page} totalPages={data.total_pages} onPageChange={(next) => setParam({ page: next })} />
    </div>
  );
}
