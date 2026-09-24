import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import EmptyState from "../../components/EmptyState.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import { StatusBadge } from "../account/Orders.jsx";
import { useToast } from "../../context/ToastContext.jsx";
import useDocumentTitle from "../../hooks/useDocumentTitle.js";
import { getAdminCustomer } from "../../services/admin.js";
import { formatCurrency, formatDate } from "../../utils/format.js";

/** Customer profile: contact info, lifetime stats, recent orders. */
export default function AdminCustomerDetail() {
  const { customerId } = useParams();
  const toast = useToast();
  const [customer, setCustomer] = useState(null);
  const [failed, setFailed] = useState(false);

  useDocumentTitle(customer ? `Admin · ${customer.first_name} ${customer.last_name}` : "Admin · Customer");

  // toast intentionally omitted from deps (fresh object per render).
  useEffect(() => {
    getAdminCustomer(customerId)
      .then(setCustomer)
      .catch((error) => {
        setFailed(true);
        toast.error(error.message || "Could not load the customer");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customerId]);

  if (failed) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center">
        <p className="font-semibold text-slate-900">Customer not found</p>
        <Link to="/admin/customers" className="mt-2 block text-sm text-brand-600 hover:underline">
          ← Back to customers
        </Link>
      </div>
    );
  }
  if (!customer) return <LoadingSpinner label="Loading customer…" />;

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/admin/customers"
          className="text-sm font-semibold text-slate-500 hover:text-slate-800"
        >
          ← All customers
        </Link>
        <h1 className="text-2xl font-extrabold text-slate-900">
          {customer.first_name} {customer.last_name}
        </h1>
        <p className="text-sm text-slate-500">
          {customer.email}
          {customer.phone && <span className="ml-2">· {customer.phone}</span>}
        </p>
      </div>

      {/* Lifetime stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Orders</p>
          <p className="mt-2 text-3xl font-extrabold text-slate-900">{customer.order_count}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Total spent</p>
          <p className="mt-2 text-3xl font-extrabold text-emerald-600">
            {formatCurrency(customer.total_spent)}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Member since</p>
          <p className="mt-2 text-xl font-extrabold text-slate-900">
            {formatDate(customer.created_at)}
          </p>
          <span
            className={`mt-2 inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${
              customer.is_active
                ? "bg-emerald-100 text-emerald-700"
                : "bg-red-100 text-red-700"
            }`}
          >
            {customer.is_active ? "Active account" : "Disabled"}
          </span>
        </div>
      </div>

      {/* Recent orders */}
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="flex items-center justify-between px-5 py-4">
          <h2 className="text-base font-bold text-slate-900">Recent orders</h2>
          <span className="text-xs text-slate-400">Latest 5</span>
        </div>
        {customer.recent_orders.length === 0 ? (
          <div className="px-5 pb-5">
            <EmptyState
              icon="🧾"
              title="No orders yet"
              description="This customer hasn't placed an order."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3">Order</th>
                  <th className="px-5 py-3">Date</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Total</th>
                  <th className="px-5 py-3 text-right">View</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {customer.recent_orders.map((order) => (
                  <tr key={order.id} className="transition hover:bg-slate-50">
                    <td className="px-5 py-3 font-semibold text-slate-900">{order.order_number}</td>
                    <td className="px-5 py-3 text-slate-500">{formatDate(order.created_at)}</td>
                    <td className="px-5 py-3">
                      <StatusBadge status={order.status} />
                    </td>
                    <td className="px-5 py-3 text-right font-semibold text-slate-900">
                      {formatCurrency(order.total)}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Link
                        to={`/admin/orders/${order.id}`}
                        className="text-sm font-semibold text-brand-600 hover:underline"
                      >
                        Manage →
                      </Link>
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
