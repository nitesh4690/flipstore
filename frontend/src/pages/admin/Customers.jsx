import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import EmptyState from "../../components/EmptyState.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import Pagination from "../../components/Pagination.jsx";
import { useToast } from "../../context/ToastContext.jsx";
import useDocumentTitle from "../../hooks/useDocumentTitle.js";
import { getAdminCustomers } from "../../services/admin.js";
import { formatCurrency, formatDate } from "../../utils/format.js";

/** Customer directory with lifetime spend (URL-driven search + pagination). */
export default function AdminCustomers() {
  useDocumentTitle("Admin · Customers");
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState(null);

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
    getAdminCustomers({ search, page, limit: 10 })
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((error) => {
        if (!cancelled) toast.error(error.message || "Could not load customers");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, page]);

  if (!data) return <LoadingSpinner label="Loading customers…" />;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900">Customers</h1>
        <p className="text-sm text-slate-500">{data.total} registered accounts</p>
      </div>

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
          placeholder="Search name or email…"
          className="h-11 w-full max-w-sm rounded-xl border border-slate-300 px-3 text-sm outline-none transition focus:border-brand-500"
        />
        <button
          type="submit"
          className="h-11 rounded-xl bg-slate-900 px-4 text-sm font-semibold text-white transition hover:bg-slate-700"
        >
          Search
        </button>
        {search && (
          <button
            type="button"
            onClick={() => {
              setSearchInput("");
              setParam({ search: "", page: 1 });
            }}
            className="h-11 rounded-xl border border-slate-300 px-4 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
          >
            Reset
          </button>
        )}
      </form>

      {data.items.length === 0 ? (
        <EmptyState
          icon="👥"
          title="No customers found"
          description={search ? `Nothing matches “${search}”.` : "Registered shoppers appear here."}
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Customer</th>
                  <th className="px-4 py-3">Joined</th>
                  <th className="px-4 py-3 text-center">Orders</th>
                  <th className="px-4 py-3 text-right">Total spent</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">View</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((customer) => (
                  <tr key={customer.id} className="transition hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <span className="font-semibold text-slate-900">
                        {customer.first_name} {customer.last_name}
                      </span>
                      <span className="block text-xs text-slate-400">{customer.email}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-500">{formatDate(customer.created_at)}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-block rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-slate-600">
                        {customer.order_count}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-slate-900">
                      {formatCurrency(customer.total_spent)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${
                          customer.is_active
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {customer.is_active ? "Active" : "Disabled"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/admin/customers/${customer.id}`}
                        className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-slate-700"
                      >
                        Profile
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <Pagination
        page={data.page}
        totalPages={data.total_pages}
        onPageChange={(next) => setParam({ page: next })}
      />
    </div>
  );
}
