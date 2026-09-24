import { useEffect, useState } from "react";

import ConfirmDialog from "../../components/ConfirmDialog.jsx";
import EmptyState from "../../components/EmptyState.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import Modal from "../../components/Modal.jsx";
import { useToast } from "../../context/ToastContext.jsx";
import useDocumentTitle from "../../hooks/useDocumentTitle.js";
import { createAddress, deleteAddress, getAddresses, updateAddress } from "../../services/shop.js";

const BLANK = {
  label: "Home",
  full_name: "",
  phone: "",
  line1: "",
  line2: "",
  city: "",
  state: "",
  postal_code: "",
  country: "United States",
  is_default_shipping: false,
  is_default_billing: false,
};

const label = "mb-1.5 block text-sm font-semibold text-slate-700";
const input =
  "h-11 w-full rounded-xl border border-slate-300 px-3 text-sm outline-none transition focus:border-brand-500";

/** Address book: list, add, edit, delete, set defaults. */
export default function Addresses() {
  useDocumentTitle("My addresses");
  const toast = useToast();
  const [rows, setRows] = useState(null); // null = loading
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null); // address being edited or null
  const [form, setForm] = useState(BLANK);
  const [saving, setSaving] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);

  const load = () =>
    getAddresses()
      .then(setRows)
      .catch((error) => {
        setRows([]);
        toast.error(error.message || "Could not load addresses");
      });

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openCreate = () => {
    setEditing(null);
    setForm(BLANK);
    setModalOpen(true);
  };

  const openEdit = (address) => {
    setEditing(address);
    setForm({ ...BLANK, ...address });
    setModalOpen(true);
  };

  const field = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  const save = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      if (editing) {
        await updateAddress(editing.id, form);
        toast.success("Address updated");
      } else {
        await createAddress(form);
        toast.success("Address saved");
      }
      setModalOpen(false);
      await load();
    } catch (error) {
      toast.error(error.message || "Could not save address");
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    try {
      await deleteAddress(pendingDelete.id);
      toast.info("Address deleted");
      await load();
    } catch (error) {
      toast.error(error.message || "Could not delete address");
    }
    setPendingDelete(null);
  };

  if (rows === null) return <LoadingSpinner label="Loading addresses…" />;

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-900">Saved addresses</h2>
        <button
          type="button"
          onClick={openCreate}
          className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          + Add address
        </button>
      </div>

      {rows.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <EmptyState
            icon="📍"
            title="No addresses yet"
            description="Save your delivery addresses for a faster checkout."
            actionLabel="Add your first address"
            onAction={openCreate}
          />
        </div>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {rows.map((address) => (
            <li
              key={address.id}
              className="rounded-2xl border border-slate-200 bg-white p-5 text-sm"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="font-bold text-slate-900">{address.label}</span>
                <span className="flex gap-1">
                  {address.is_default_shipping && (
                    <span className="rounded-full bg-brand-50 px-2 py-0.5 text-[10px] font-bold uppercase text-brand-600">
                      shipping
                    </span>
                  )}
                  {address.is_default_billing && (
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-500">
                      billing
                    </span>
                  )}
                </span>
              </div>
              <p className="mt-2 font-medium text-slate-700">{address.full_name}</p>
              <p className="text-slate-600">
                {address.line1}
                {address.line2 ? `, ${address.line2}` : ""}, {address.city}
                {address.state ? `, ${address.state}` : ""} {address.postal_code},{" "}
                {address.country}
              </p>
              {address.phone && <p className="mt-1 text-slate-500">{address.phone}</p>}
              <div className="mt-3 flex gap-3 text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => openEdit(address)}
                  className="text-brand-600 hover:underline"
                >
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() => setPendingDelete(address)}
                  className="text-red-500 hover:underline"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? "Edit address" : "Add address"}
        maxWidth="max-w-2xl"
      >
        <form onSubmit={save} className="grid max-h-[70vh] gap-4 overflow-y-auto sm:grid-cols-2">
          {[
            ["label", "Label", "text"],
            ["full_name", "Full name", "text"],
            ["phone", "Phone (optional)", "tel"],
            ["line1", "Address line 1", "text"],
            ["line2", "Address line 2 (optional)", "text"],
            ["city", "City", "text"],
            ["state", "State / Province", "text"],
            ["postal_code", "Postal code", "text"],
            ["country", "Country", "text"],
          ].map(([key, name, type]) => (
            <div key={key} className={key === "line1" || key === "line2" ? "sm:col-span-2" : ""}>
              <label htmlFor={`ad-${key}`} className={label}>{name}</label>
              <input
                id={`ad-${key}`}
                type={type}
                required={["full_name", "line1", "city", "postal_code", "country"].includes(key)}
                value={form[key]}
                onChange={(event) => field(key, event.target.value)}
                className={input}
              />
            </div>
          ))}
          <div className="flex items-center gap-4 sm:col-span-2">
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={form.is_default_shipping}
                onChange={(event) => field("is_default_shipping", event.target.checked)}
                className="h-4 w-4 accent-brand-600"
              />
              Default for shipping
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={form.is_default_billing}
                onChange={(event) => field("is_default_billing", event.target.checked)}
                className="h-4 w-4 accent-brand-600"
              />
              Default for billing
            </label>
          </div>
          <div className="flex justify-end gap-3 sm:col-span-2">
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              className="rounded-xl border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {saving ? "Saving…" : "Save address"}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete address?"
        message={pendingDelete ? `Remove “${pendingDelete.label}” from your address book?` : ""}
        confirmLabel="Delete"
        danger
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </section>
  );
}
