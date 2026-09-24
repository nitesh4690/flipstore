import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import { StatusBadge } from "../account/Orders.jsx";
import { useToast } from "../../context/ToastContext.jsx";
import useDocumentTitle from "../../hooks/useDocumentTitle.js";
import { getStats } from "../../services/admin.js";
import { formatCurrency, formatDate } from "../../utils/format.js";

/** Single KPI tile. */
function StatCard({ label, value, accent = "text-slate-900", hint }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-3xl font-extrabold ${accent}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

/** Admin dashboard: KPI cards, 7-day revenue chart, recent orders, low stock. */
export default function AdminDashboard() {
  useDocumentTitle("Admin · Dashboard");
  const toast = useToast();
  const [stats, setStats] = useState(null);
  const [failed, setFailed] = useState(false);

  // toast intentionally omitted from deps (fresh object per render).
  useEffect(() => {
    let cancelled = false;
    getStats()
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch((error) => {
        if (!cancelled) {
          setFailed(true);
          toast.error(error.message || "Could not load dashboard");
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (failed) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center">
        <p className="font-semibold text-slate-900">Could not load the dashboard</p>
        <p className="mt-1 text-sm text-slate-500">Check that the API server is running.</p>
      </div>
    );
  }
  if (!stats) return <LoadingSpinner label="Loading dashboard…" />;

  const maxRevenue = Math.max(...stats.revenue_last_7_days.map((point) => point.revenue), 1);
  const pending = stats.orders_by_status.pending + stats.orders_by_status.confirmed;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500">Store performance at a glance.</p>
      </div>

      {/* KPI cards */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Revenue"
          value={formatCurrency(stats.revenue)}
          accent="text-emerald-600"
          hint="All orders except cancelled"
        />
        <StatCard
          label="Orders"
          value={stats.order_count}
          hint={`${pending} awaiting fulfilment`}
        />
        <StatCard label="Customers" value={stats.customer_count} hint="Registered accounts" />
        <StatCard
          label="Products"
          value={stats.product_count}
          accent={stats.low_stock_count > 0 ? "text-amber-600" : "text-slate-900"}
          hint={
            stats.low_stock_count > 0
              ? `${stats.low_stock_count} low on stock`
              : "Inventory healthy"
          }
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[3fr_2fr]">
        {/* 7-day revenue chart */}
        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-base font-bold text-slate-900">Revenue — last 7 days</h2>
          <div className="mt-5 flex h-44 items-end gap-2" role="img" aria-label="Daily revenue bar chart">
            {stats.revenue_last_7_days.map((point) => (
              <div key={point.date} className="flex h-full flex-1 flex-col justify-end gap-1.5">
                <span className="text-center text-[10px] font-semibold text-slate-400">
                  {point.revenue > 0 ? formatCurrency(point.revenue) : ""}
                </span>
                <div
                  title={`${point.date}: ${formatCurrency(point.revenue)}`}
                  className="w-full rounded-t-md bg-gradient-to-t from-brand-600 to-violet-500 transition hover:from-brand-700 hover:to-violet-600"
                  style={{
                    height: `${Math.max((point.revenue / maxRevenue) * 100, point.revenue > 0 ? 4 : 1)}%`,
                  }}
                />
                <span className="text-center text-[10px] text-slate-400">
                  {new Date(`${point.date}T00:00:00`).toLocaleDateString("en-US", { weekday: "short" }).slice(0, 3)}
                </span>
              </div>
            ))}
          </div>

          {/* Orders by status */}
          <div className="mt-5 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
            {Object.entries(stats.orders_by_status).map(([status, count]) => (
              <span
                key={status}
                className="flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600"
              >
                <span className="capitalize">{status}</span>
                <span className="grid h-5 min-w-5 place-items-center rounded-full bg-white px-1 text-[11px] font-bold">
                  {count}
                </span>
              </span>
            ))}
          </div>
        </section>

        {/* Low stock */}
        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-base font-bold text-slate-900">Low stock</h2>
          {stats.low_stock.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">
              All products have healthy inventory 🎉
            </p>
          ) : (
            <ul className="mt-3 divide-y divide-slate-100">
              {stats.low_stock.map((product) => (
                <li key={product.id} className="flex items-center justify-between gap-3 py-2.5">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-900">{product.name}</p>
                    <p className="text-xs text-slate-400">SKU {product.sku}</p>
                  </div>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-bold ${
                      product.stock === 0
                        ? "bg-red-100 text-red-700"
                        : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {product.stock} left
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Recent orders */}
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="flex items-center justify-between px-5 py-4">
          <h2 className="text-base font-bold text-slate-900">Recent orders</h2>
          <Link to="/admin/orders" className="text-sm font-semibold text-brand-600 hover:underline">
            View all →
          </Link>
        </div>
        {stats.recent_orders.length === 0 ? (
          <p className="px-5 pb-5 text-sm text-slate-500">No orders yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3">Order</th>
                  <th className="px-5 py-3">Customer</th>
                  <th className="px-5 py-3">Date</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {stats.recent_orders.map((order) => (
                  <tr key={order.id} className="transition hover:bg-slate-50">
                    <td className="px-5 py-3">
                      <Link
                        to={`/admin/orders/${order.id}`}
                        className="font-semibold text-brand-600 hover:underline"
                      >
                        {order.order_number}
                      </Link>
                    </td>
                    <td className="max-w-48 truncate px-5 py-3 text-slate-600">
                      {order.customer?.email}
                    </td>
                    <td className="px-5 py-3 text-slate-500">{formatDate(order.created_at)}</td>
                    <td className="px-5 py-3">
                      <StatusBadge status={order.status} />
                    </td>
                    <td className="px-5 py-3 text-right font-semibold text-slate-900">
                      {formatCurrency(order.total)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
