import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import { StatusBadge } from "../account/Orders.jsx";
import { useToast } from "../../context/ToastContext.jsx";
import useDocumentTitle from "../../hooks/useDocumentTitle.js";
import { getAdminOrder, updateAdminOrder } from "../../services/admin.js";
import { formatCurrency, formatDate } from "../../utils/format.js";

const STATUS_OPTIONS = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"];
const PAYMENT_OPTIONS = ["pending", "paid", "failed", "refunded"];
const SHIPPING_OPTIONS = ["pending", "shipped", "delivered", "returned"];

const moneyRow = (label, value, accent = false) => (
  <div className="flex justify-between py-1">
    <dt className="text-slate-500">{label}</dt>
    <dd className={`font-semibold ${accent ? "text-emerald-600" : "text-slate-900"}`}>{value}</dd>
  </div>
);

function AddressBlock({ title, address }) {
  if (!address) return null;
  return (
    <div className="rounded-xl border border-slate-200 p-4 text-sm">
      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-1 font-semibold text-slate-900">{address.full_name}</p>
      <p className="text-slate-600">
        {address.line1}
        {address.line2 ? `, ${address.line2}` : ""}, {address.city}
        {address.state ? `, ${address.state}` : ""} {address.postal_code}, {address.country}
      </p>
      {address.phone && <p className="mt-1 text-slate-500">{address.phone}</p>}
    </div>
  );
}

/** Status control: labelled <select> that PATCHes immediately on change. */
function StatusSelect({ label, value, options, onChange, disabled }) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-slate-500">
        {label}
      </label>
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm font-medium capitalize outline-none transition focus:border-brand-500 disabled:opacity-60"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Admin order detail: manage lifecycle statuses, inspect items/totals/address. */
export default function AdminOrderDetail() {
  const { orderId } = useParams();
  const toast = useToast();
  const [order, setOrder] = useState(null);
  const [failed, setFailed] = useState(false);
  const [saving, setSaving] = useState(false);

  useDocumentTitle(order ? `Admin · ${order.order_number}` : "Admin · Order");

  // toast intentionally omitted from deps (fresh object per render).
  useEffect(() => {
    getAdminOrder(orderId)
      .then(setOrder)
      .catch((error) => {
        setFailed(true);
        toast.error(error.message || "Could not load the order");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  const changeStatus = async (field, value) => {
    if (!order || order[field] === value) return;
    setSaving(true);
    try {
      const updated = await updateAdminOrder(orderId, { [field]: value });
      setOrder(updated);
      toast.success("Order updated");
    } catch (error) {
      toast.error(error.message || "Could not update the order");
    } finally {
      setSaving(false);
    }
  };

  if (failed) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center">
        <p className="font-semibold text-slate-900">Order not found</p>
        <Link to="/admin/orders" className="mt-2 block text-sm text-brand-600 hover:underline">
          ← Back to orders
        </Link>
      </div>
    );
  }
  if (!order) return <LoadingSpinner label="Loading order…" />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link
            to="/admin/orders"
            className="text-sm font-semibold text-slate-500 hover:text-slate-800"
          >
            ← All orders
          </Link>
          <h1 className="text-2xl font-extrabold text-slate-900">{order.order_number}</h1>
          <p className="text-sm text-slate-500">
            Placed {formatDate(order.created_at)} by{" "}
            <Link
              to={`/admin/customers/${order.customer?.id}`}
              className="font-semibold text-brand-600 hover:underline"
            >
              {order.customer?.email}
            </Link>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusBadge status={order.status} />
          <StatusBadge status={order.payment_status} />
          <StatusBadge status={order.shipping_status} />
        </div>
      </div>

      {/* Lifecycle controls */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="text-base font-bold text-slate-900">Manage fulfillment</h2>
        <p className="mb-4 text-sm text-slate-500">
          Changes save immediately and are visible to the customer.
        </p>
        <div className="grid gap-4 sm:grid-cols-3">
          <StatusSelect
            label="Order status"
            value={order.status}
            options={STATUS_OPTIONS}
            onChange={(value) => changeStatus("status", value)}
            disabled={saving}
          />
          <StatusSelect
            label="Payment status"
            value={order.payment_status}
            options={PAYMENT_OPTIONS}
            onChange={(value) => changeStatus("payment_status", value)}
            disabled={saving}
          />
          <StatusSelect
            label="Shipping status"
            value={order.shipping_status}
            options={SHIPPING_OPTIONS}
            onChange={(value) => changeStatus("shipping_status", value)}
            disabled={saving}
          />
        </div>
        {order.notes && (
          <div className="mt-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-800">
            <span className="font-bold">Customer note:</span> {order.notes}
          </div>
        )}
      </section>

      {/* Items */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Item</th>
              <th className="px-4 py-3 text-center">Qty</th>
              <th className="px-4 py-3 text-right">Price</th>
              <th className="px-4 py-3 text-right">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {order.items.map((item) => (
              <tr key={item.id}>
                <td className="px-4 py-3">
                  <span className="font-medium text-slate-900">{item.product_name}</span>
                  {item.variant_name && (
                    <span className="block text-xs text-slate-500">{item.variant_name}</span>
                  )}
                  <span className="block text-xs text-slate-400">SKU {item.sku}</span>
                </td>
                <td className="px-4 py-3 text-center text-slate-600">{item.quantity}</td>
                <td className="px-4 py-3 text-right text-slate-600">
                  {formatCurrency(item.unit_price)}
                </td>
                <td className="px-4 py-3 text-right font-semibold text-slate-900">
                  {formatCurrency(item.total)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-4">
          <AddressBlock title="Shipping address" address={order.shipping_address} />
          <AddressBlock title="Billing address" address={order.billing_address} />

          {order.payments?.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Payments</p>
              {order.payments.map((payment) => (
                <div key={payment.id} className="mt-2 flex items-center justify-between">
                  <span className="text-slate-600 capitalize">
                    {payment.method === "card_mock" ? "Card (mock)" : payment.method} ·{" "}
                    <span className="text-xs text-slate-400">{payment.transaction_id}</span>
                  </span>
                  <span className="flex items-center gap-2 font-semibold text-slate-900">
                    {formatCurrency(payment.amount)}
                    <StatusBadge status={payment.status} />
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="h-fit rounded-2xl border border-slate-200 bg-white p-5 text-sm">
          <h3 className="text-base font-bold text-slate-900">Summary</h3>
          <dl className="mt-3">
            {moneyRow("Subtotal", formatCurrency(order.subtotal))}
            {order.discount > 0 && moneyRow("Discount", `−${formatCurrency(order.discount)}`, true)}
            {moneyRow(
              "Shipping",
              order.shipping_cost === 0 ? "FREE" : formatCurrency(order.shipping_cost),
            )}
            {moneyRow("Tax", formatCurrency(order.tax))}
            <div className="mt-1 flex justify-between border-t border-slate-100 pt-2 text-base">
              <dt className="font-bold text-slate-900">Total</dt>
              <dd className="font-extrabold text-slate-900">{formatCurrency(order.total)}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}
