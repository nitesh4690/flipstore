import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import ConfirmDialog from "../../components/ConfirmDialog.jsx";
import EmptyState from "../../components/EmptyState.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import Modal from "../../components/Modal.jsx";
import Pagination from "../../components/Pagination.jsx";
import { useToast } from "../../context/ToastContext.jsx";
import useDocumentTitle from "../../hooks/useDocumentTitle.js";
import { createCoupon, deleteCoupon, getCoupons, updateCoupon } from "../../services/admin.js";
import { formatCurrency, formatDate } from "../../utils/format.js";

const label = "mb-1.5 block text-sm font-semibold text-slate-700";
const input =
  "h-11 w-full rounded-xl border border-slate-300 px-3 text-sm outline-none transition focus:border-brand-500";

const EMPTY = {
  code: "",
  discount_type: "percentage",
  value: "",
  min_order_amount: "",
  max_uses: "",
  starts_at: "",
  expires_at: "",
  is_active: true,
};

/** datetime-local value ← ISO string (local time display) */
function toInputValue(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

function DiscountBadge({ coupon }) {
  return (
    <span className="inline-block rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-bold text-brand-700">
      {coupon.discount_type === "percentage"
        ? `${coupon.value}% off`
        : `${formatCurrency(coupon.value)} off`}
    </span>
  );
}

function ActiveBadge({ active }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${
        active ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-600"
      }`}
    >
      {active ? "Active" : "Paused"}
    </span>
  );
}

/** Admin coupon manager: search, pagination, create/edit modal, toggle, delete. */
export default function AdminCoupons() {
  useDocumentTitle("Admin · Coupons");
  const toast = useToast();
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null); // coupon row | null = create
  const [deleting, setDeleting] = useState(null); // coupon row

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: EMPTY });

  const discountType = watch("discount_type");

  const load = () => {
    getCoupons({ page, limit: 10, search: appliedSearch })
      .then(setData)
      .catch((error) => {
        setData({ items: [], total: 0, page: 1, total_pages: 0 });
        toast.error(error.message || "Could not load coupons");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, appliedSearch]);

  const openCreate = () => {
    setEditing(null);
    reset(EMPTY);
    setModalOpen(true);
  };

  const openEdit = (row) => {
    setEditing(row);
    reset({
      code: row.code,
      discount_type: row.discount_type,
      value: String(row.value),
      min_order_amount: String(row.min_order_amount ?? 0),
      max_uses: row.max_uses == null ? "" : String(row.max_uses),
      starts_at: toInputValue(row.starts_at),
      expires_at: toInputValue(row.expires_at),
      is_active: row.is_active,
    });
    setModalOpen(true);
  };

  const buildPayload = (values) => ({
    code: values.code.trim().toUpperCase(),
    discount_type: values.discount_type,
    value: Number(values.value),
    min_order_amount: values.min_order_amount === "" ? 0 : Number(values.min_order_amount),
    max_uses: values.max_uses === "" ? null : Number(values.max_uses),
    starts_at: values.starts_at ? new Date(values.starts_at).toISOString() : null,
    expires_at: values.expires_at ? new Date(values.expires_at).toISOString() : null,
    is_active: Boolean(values.is_active),
  });

  const onSubmit = async (values) => {
    try {
      const payload = buildPayload(values);
      if (editing) {
        await updateCoupon(editing.id, payload);
        toast.success(`Coupon ${payload.code} updated`);
      } else {
        await createCoupon(payload);
        toast.success(`Coupon ${payload.code} created`);
      }
      setModalOpen(false);
      load();
    } catch (error) {
      toast.error(error.message || "Could not save coupon");
    }
  };

  const toggleActive = async (row) => {
    try {
      await updateCoupon(row.id, {
        code: row.code,
        discount_type: row.discount_type,
        value: Number(row.value),
        min_order_amount: Number(row.min_order_amount ?? 0),
        max_uses: row.max_uses,
        starts_at: row.starts_at,
        expires_at: row.expires_at,
        is_active: !row.is_active,
      });
      toast.success(`Coupon ${row.code} ${row.is_active ? "paused" : "activated"}`);
      load();
    } catch (error) {
      toast.error(error.message || "Could not update coupon");
    }
  };

  const confirmDelete = async () => {
    try {
      await deleteCoupon(deleting.id);
      toast.success(`Coupon ${deleting.code} deleted`);
      setDeleting(null);
      load();
    } catch (error) {
      toast.error(error.message || "Could not delete coupon");
      setDeleting(null);
    }
  };

  if (!data) return <LoadingSpinner label="Loading coupons…" />;

  const applySearch = (event) => {
    event.preventDefault();
    setPage(1);
    setAppliedSearch(search.trim());
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900">Coupons</h1>
          <p className="text-sm text-slate-500">{data.total} discount codes</p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          + New coupon
        </button>
      </div>

      <form onSubmit={applySearch} className="flex max-w-md gap-2">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search by code…"
          className="h-11 w-full rounded-xl border border-slate-300 px-3 text-sm outline-none transition focus:border-brand-500"
        />
        <button
          type="submit"
          className="rounded-xl border border-slate-300 px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          Search
        </button>
      </form>

      {data.items.length === 0 ? (
        <EmptyState
          icon="🎟️"
          title={appliedSearch ? "No matching coupons" : "No coupons yet"}
          description={
            appliedSearch
              ? "Try a different search term."
              : "Create discount codes your customers can apply at checkout."
          }
          actionLabel={appliedSearch ? undefined : "New coupon"}
          onAction={appliedSearch ? undefined : openCreate}
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Code</th>
                  <th className="px-4 py-3">Discount</th>
                  <th className="px-4 py-3">Min. order</th>
                  <th className="px-4 py-3 text-center">Used</th>
                  <th className="px-4 py-3">Window</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((row) => (
                  <tr key={row.id} className="transition hover:bg-slate-50">
                    <td className="px-4 py-3 font-bold uppercase tracking-wide text-slate-900">
                      {row.code}
                    </td>
                    <td className="px-4 py-3">
                      <DiscountBadge coupon={row} />
                    </td>
                    <td className="px-4 py-3 text-slate-500">
                      {Number(row.min_order_amount) > 0
                        ? formatCurrency(row.min_order_amount)
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-block rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-slate-600">
                        {row.used_count}
                        {row.max_uses != null ? ` / ${row.max_uses}` : ""}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {row.starts_at || row.expires_at
                        ? `${row.starts_at ? formatDate(row.starts_at) : "Now"} → ${
                            row.expires_at ? formatDate(row.expires_at) : "No expiry"
                          }`
                        : "Always"}
                    </td>
                    <td className="px-4 py-3">
                      <ActiveBadge active={row.is_active} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => openEdit(row)}
                          className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-100"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => toggleActive(row)}
                          className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-100"
                        >
                          {row.is_active ? "Pause" : "Activate"}
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeleting(row)}
                          className="rounded-lg border border-red-100 px-3 py-1.5 text-xs font-semibold text-red-600 transition hover:bg-red-50"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <Pagination page={data.page} totalPages={data.total_pages} onPageChange={setPage} />

      {/* Create / edit modal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? `Edit coupon ${editing.code}` : "New coupon"}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="c-code" className={label}>Code *</label>
              <input
                id="c-code"
                placeholder="SUMMER10"
                className={`${input} uppercase ${errors.code ? "border-red-400" : ""}`}
                {...register("code", {
                  required: "Code is required",
                  pattern: {
                    value: /^[A-Za-z0-9]{3,50}$/,
                    message: "3–50 letters or numbers only",
                  },
                })}
              />
              {errors.code && <p className="mt-1 text-xs text-red-600">{errors.code.message}</p>}
            </div>

            <div>
              <label htmlFor="c-type" className={label}>Discount type</label>
              <select id="c-type" className={input} {...register("discount_type")}>
                <option value="percentage">Percentage (%)</option>
                <option value="fixed">Fixed amount ($)</option>
              </select>
            </div>

            <div>
              <label htmlFor="c-value" className={label}>Value *</label>
              <input
                id="c-value"
                type="number"
                step="0.01"
                min="0.01"
                placeholder={discountType === "percentage" ? "10" : "15"}
                className={`${input} ${errors.value ? "border-red-400" : ""}`}
                {...register("value", {
                  required: "Value is required",
                  validate: (raw) => {
                    const value = Number(raw);
                    if (!(value > 0)) return "Must be greater than 0";
                    if (discountType === "percentage" && value > 100)
                      return "Percentage cannot exceed 100";
                    return true;
                  },
                })}
              />
              {errors.value && <p className="mt-1 text-xs text-red-600">{errors.value.message}</p>}
            </div>

            <div>
              <label htmlFor="c-min" className={label}>Min. order ($)</label>
              <input
                id="c-min"
                type="number"
                step="0.01"
                min="0"
                placeholder="0 = no minimum"
                className={input}
                {...register("min_order_amount")}
              />
            </div>

            <div>
              <label htmlFor="c-max" className={label}>Usage limit</label>
              <input
                id="c-max"
                type="number"
                min="1"
                placeholder="∞ = unlimited"
                className={`${input} ${errors.max_uses ? "border-red-400" : ""}`}
                {...register("max_uses", {
                  validate: (raw) =>
                    raw === "" || Number(raw) >= 1 || "Must be at least 1",
                })}
              />
              {errors.max_uses && (
                <p className="mt-1 text-xs text-red-600">{errors.max_uses.message}</p>
              )}
            </div>

            <div className="self-end">
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-brand-600"
                  {...register("is_active")}
                />
                Active (usable at checkout)
              </label>
            </div>

            <div>
              <label htmlFor="c-starts" className={label}>Starts</label>
              <input
                id="c-starts"
                type="datetime-local"
                className={input}
                {...register("starts_at")}
              />
            </div>

            <div>
              <label htmlFor="c-expires" className={label}>Expires</label>
              <input
                id="c-expires"
                type="datetime-local"
                className={`${input} ${errors.expires_at ? "border-red-400" : ""}`}
                {...register("expires_at", {
                  validate: (raw) => {
                    if (!raw) return true;
                    const starts = watch("starts_at");
                    if (starts && new Date(raw) <= new Date(starts))
                      return "Must be after the start date";
                    return true;
                  },
                })}
              />
              {errors.expires_at && (
                <p className="mt-1 text-xs text-red-600">{errors.expires_at.message}</p>
              )}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-xl bg-brand-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {isSubmitting ? "Saving…" : editing ? "Save changes" : "Create"}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(deleting)}
        title="Delete coupon?"
        message={`“${deleting?.code}” will be removed. Orders that already used it keep their discounts.`}
        confirmLabel="Delete"
        danger
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(null)}
      />
    </div>
  );
}
