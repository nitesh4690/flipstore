import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import ConfirmDialog from "../../components/ConfirmDialog.jsx";
import EmptyState from "../../components/EmptyState.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import Modal from "../../components/Modal.jsx";
import { useToast } from "../../context/ToastContext.jsx";
import useDocumentTitle from "../../hooks/useDocumentTitle.js";
import {
  createBrand,
  createCategory,
  deleteBrand,
  deleteCategory,
  getAdminBrands,
  getAdminCategories,
  updateBrand,
  updateCategory,
} from "../../services/admin.js";
import { formatDate } from "../../utils/format.js";

const label = "mb-1.5 block text-sm font-semibold text-slate-700";
const input =
  "h-11 w-full rounded-xl border border-slate-300 px-3 text-sm outline-none transition focus:border-brand-500";

function ActiveBadge({ active }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${
        active ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-600"
      }`}
    >
      {active ? "Active" : "Hidden"}
    </span>
  );
}

/** Tab strip shared by the category and brand tables. */
function Tabs({ active, onChange }) {
  const tabs = [
    { id: "categories", label: "Categories" },
    { id: "brands", label: "Brands" },
  ];
  return (
    <div className="flex gap-2">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
            active === tab.id
              ? "bg-slate-900 text-white"
              : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

/** Admin taxonomy manager: categories (with parent) and brands. */
export default function AdminCategories() {
  useDocumentTitle("Admin · Categories");
  const toast = useToast();
  const [tab, setTab] = useState("categories");
  const [categories, setCategories] = useState(null);
  const [brands, setBrands] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null); // {kind, row}
  const [deleting, setDeleting] = useState(null); // {kind, row}

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: { name: "", slug: "", description: "", parent_id: "", is_active: true },
  });

  const load = () => {
    getAdminCategories().then(setCategories).catch((error) => {
      setCategories([]);
      toast.error(error.message || "Could not load categories");
    });
    getAdminBrands().then(setBrands).catch((error) => {
      setBrands([]);
      toast.error(error.message || "Could not load brands");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openCreate = () => {
    setEditing({ kind: tab, row: null });
    reset({ name: "", slug: "", description: "", parent_id: "", is_active: true });
    setModalOpen(true);
  };

  const openEdit = (kind, row) => {
    setEditing({ kind, row });
    reset({
      name: row.name,
      slug: row.slug ?? "",
      description: row.description ?? "",
      parent_id: row.parent_id ?? "",
      is_active: row.is_active,
    });
    setModalOpen(true);
  };

  const onSubmit = async (values) => {
    const kind = editing.kind;
    const payload = {
      name: values.name.trim(),
      slug: values.slug.trim() || null,
      is_active: Boolean(values.is_active),
    };
    if (kind === "categories") {
      payload.description = values.description || null;
      payload.parent_id = values.parent_id || null;
    }

    try {
      if (editing.row) {
        await (kind === "categories"
          ? updateCategory(editing.row.id, payload)
          : updateBrand(editing.row.id, payload));
        toast.success(`${kind === "categories" ? "Category" : "Brand"} updated`);
      } else {
        await (kind === "categories" ? createCategory(payload) : createBrand(payload));
        toast.success(`${kind === "categories" ? "Category" : "Brand"} created`);
      }
      setModalOpen(false);
      load();
    } catch (error) {
      toast.error(error.message || "Could not save");
    }
  };

  const confirmDelete = async () => {
    const { kind, row } = deleting;
    try {
      await (kind === "categories" ? deleteCategory(row.id) : deleteBrand(row.id));
      toast.success(`“${row.name}” deleted`);
      setDeleting(null);
      load();
    } catch (error) {
      toast.error(error.message || "Could not delete");
      setDeleting(null);
    }
  };

  if (!categories || !brands) return <LoadingSpinner label="Loading taxonomy…" />;

  // Parent options exclude the row being edited and its own subtree (1 level deep here)
  const parentOptions = categories.filter((row) => row.id !== editing?.row?.id);

  const rows = tab === "categories" ? categories : brands;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900">Categories & brands</h1>
          <p className="text-sm text-slate-500">
            {categories.length} categories · {brands.length} brands
          </p>
        </div>
        <div className="flex gap-2">
          <Tabs active={tab} onChange={setTab} />
          <button
            type="button"
            onClick={openCreate}
            className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
          >
            + New {tab === "categories" ? "category" : "brand"}
          </button>
        </div>
      </div>

      {rows.length === 0 ? (
        <EmptyState
          icon="🏷️"
          title={`No ${tab} yet`}
          description={`Create your first ${tab === "categories" ? "category" : "brand"} to organize the catalog.`}
          actionLabel={`New ${tab === "categories" ? "category" : "brand"}`}
          onAction={openCreate}
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Slug</th>
                  {tab === "categories" && <th className="px-4 py-3">Parent</th>}
                  <th className="px-4 py-3 text-center">Products</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((row) => {
                  const parent =
                    tab === "categories" && row.parent_id
                      ? categories.find((c) => c.id === row.parent_id)?.name
                      : null;
                  return (
                    <tr key={row.id} className="transition hover:bg-slate-50">
                      <td className="px-4 py-3 font-semibold text-slate-900">{row.name}</td>
                      <td className="px-4 py-3 text-slate-500">{row.slug}</td>
                      {tab === "categories" && (
                        <td className="px-4 py-3 text-slate-500">{parent ?? "—"}</td>
                      )}
                      <td className="px-4 py-3 text-center">
                        <span className="inline-block rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-slate-600">
                          {row.product_count ?? 0}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <ActiveBadge active={row.is_active} />
                      </td>
                      <td className="px-4 py-3 text-slate-500">{formatDate(row.created_at)}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => openEdit(tab, row)}
                            className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-100"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => setDeleting({ kind: tab, row })}
                            className="rounded-lg border border-red-100 px-3 py-1.5 text-xs font-semibold text-red-600 transition hover:bg-red-50"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Create / edit modal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={
          editing?.row
            ? `Edit ${editing.kind === "categories" ? "category" : "brand"}`
            : `New ${editing?.kind === "brands" ? "brand" : "category"}`
        }
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label htmlFor="t-name" className={label}>Name *</label>
            <input
              id="t-name"
              className={`${input} ${errors.name ? "border-red-400" : ""}`}
              {...register("name", { required: "Name is required", minLength: 2 })}
            />
            {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
          </div>

          <div>
            <label htmlFor="t-slug" className={label}>Slug</label>
            <input
              id="t-slug"
              placeholder="auto-generated when empty"
              className={input}
              {...register("slug")}
            />
          </div>

          {editing?.kind !== "brands" && (
            <>
              <div>
                <label htmlFor="t-parent" className={label}>Parent category</label>
                <select id="t-parent" className={input} {...register("parent_id")}>
                  <option value="">— None (top level) —</option>
                  {parentOptions.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="t-description" className={label}>Description</label>
                <textarea
                  id="t-description"
                  rows="2"
                  className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-brand-500"
                  {...register("description")}
                />
              </div>
            </>
          )}

          <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <input type="checkbox" className="h-4 w-4 accent-brand-600" {...register("is_active")} />
            Active (visible in store)
          </label>

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
              {isSubmitting ? "Saving…" : editing?.row ? "Save changes" : "Create"}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(deleting)}
        title={`Delete ${deleting?.kind === "brands" ? "brand" : "category"}?`}
        message={`“${deleting?.row?.name}” will be removed. Products referencing it become uncategorized.`}
        confirmLabel="Delete"
        danger
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(null)}
      />
    </div>
  );
}
