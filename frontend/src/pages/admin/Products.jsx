import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";

import ConfirmDialog from "../../components/ConfirmDialog.jsx";
import EmptyState from "../../components/EmptyState.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import Modal from "../../components/Modal.jsx";
import Pagination from "../../components/Pagination.jsx";
import { useToast } from "../../context/ToastContext.jsx";
import useDocumentTitle from "../../hooks/useDocumentTitle.js";
import { fetchProduct } from "../../services/catalog.js";
import {
  createProduct,
  deleteProduct,
  getAdminBrands,
  getAdminCategories,
  getAdminProducts,
  updateProduct,
} from "../../services/admin.js";
import { IMAGE_FALLBACK, formatCurrency } from "../../utils/format.js";

const label = "mb-1.5 block text-sm font-semibold text-slate-700";
const input =
  "h-11 w-full rounded-xl border border-slate-300 px-3 text-sm outline-none transition focus:border-brand-500";

function StockBadge({ stock }) {
  const style =
    stock === 0
      ? "bg-red-100 text-red-700"
      : stock <= 5
        ? "bg-amber-100 text-amber-700"
        : "bg-emerald-100 text-emerald-700";
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${style}`}>
      {stock}
    </span>
  );
}

/** Admin product manager: search, pagination, create/edit modal, delete. */
export default function AdminProducts() {
  useDocumentTitle("Admin · Products");
  const toast = useToast();
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null); // product being edited (null = create)
  const [deleting, setDeleting] = useState(null);
  const [categories, setCategories] = useState([]);
  const [brands, setBrands] = useState([]);
  // Edit form holds full product data (the admin list payload omits description)
  const [detailLoaded, setDetailLoaded] = useState(false);
  const editSeq = useRef(0); // cancels stale detail hydrations

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: {
      name: "",
      sku: "",
      description: "",
      price: "",
      sale_price: "",
      stock: 0,
      category_id: "",
      brand_id: "",
      image_url: "",
      is_active: true,
      is_featured: false,
    },
  });

  // toast intentionally omitted from deps (fresh object per render).
  useEffect(() => {
    let cancelled = false;
    getAdminProducts({ search: appliedSearch, page, limit: 10 })
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((error) => {
        if (!cancelled) toast.error(error.message || "Could not load products");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, appliedSearch]);

  useEffect(() => {
    getAdminCategories().then(setCategories).catch(() => setCategories([]));
    getAdminBrands().then(setBrands).catch(() => setBrands([]));
  }, []);

  const openCreate = () => {
    editSeq.current += 1; // invalidate any in-flight edit hydration
    setEditing(null);
    setDetailLoaded(true); // create form owns every field
    reset({
      name: "",
      sku: "",
      description: "",
      price: "",
      sale_price: "",
      stock: 0,
      category_id: "",
      brand_id: "",
      image_url: "",
      is_active: true,
      is_featured: false,
    });
    setModalOpen(true);
  };

  const openEdit = (product) => {
    const seq = ++editSeq.current;
    setEditing(product);
    setDetailLoaded(false);
    reset({
      name: product.name,
      sku: product.sku,
      description: product.description ?? "",
      price: String(product.price),
      sale_price: product.sale_price != null ? String(product.sale_price) : "",
      stock: product.stock,
      category_id: product.category_id ?? "",
      brand_id: product.brand_id ?? "",
      image_url: product.primary_image_url ?? "",
      is_active: product.is_active,
      is_featured: product.is_featured,
    });
    setModalOpen(true);

    // The admin list payload is lightweight (no description) — hydrate the
    // full detail so an update can never wipe fields we never loaded.
    fetchProduct(product.id)
      .then((detail) => {
        if (seq !== editSeq.current) return; // a newer modal opened meanwhile
        const primary =
          detail.images?.find((image) => image.is_primary)?.url ??
          detail.images?.[0]?.url ??
          null;
        const merged = { ...product, ...detail, primary_image_url: primary };
        setEditing(merged);
        setDetailLoaded(true);
        reset({
          name: merged.name,
          sku: merged.sku,
          description: merged.description ?? "",
          price: String(merged.price),
          sale_price: merged.sale_price != null ? String(merged.sale_price) : "",
          stock: merged.stock,
          category_id: merged.category_id ?? "",
          brand_id: merged.brand_id ?? "",
          image_url: primary ?? "",
          is_active: merged.is_active,
          is_featured: merged.is_featured,
        });
      })
      .catch(() => {
        // Keep the lightweight values; onSubmit omits description until hydrated.
        if (seq === editSeq.current) setDetailLoaded(false);
      });
  };

  const onSubmit = async (values) => {
    const payload = {
      name: values.name.trim(),
      price: Number(values.price),
      sale_price: values.sale_price === "" ? null : Number(values.sale_price),
      stock: Number(values.stock),
      category_id: values.category_id || null,
      brand_id: values.brand_id || null,
      is_active: Boolean(values.is_active),
      is_featured: Boolean(values.is_featured),
    };
    // Description: only send it once the full detail has hydrated — omitting
    // the key leaves the stored value untouched (exclude_unset server-side).
    if (detailLoaded) payload.description = values.description ?? "";

    // SKU: auto-generate on create; keep the existing one when the field is blank
    if (values.sku.trim()) payload.sku = values.sku.trim();
    else if (editing) payload.sku = editing.sku;

    // Primary image: send `images` only when the field changed (sending it
    // replaces the whole list server-side); clearing the field clears the list.
    const imageUrl = values.image_url.trim();
    const currentImage = editing?.primary_image_url ?? "";
    if (imageUrl !== currentImage) {
      payload.images = imageUrl ? [{ url: imageUrl, is_primary: true }] : [];
    }

    try {
      if (editing) {
        await updateProduct(editing.id, payload);
        toast.success("Product updated");
      } else {
        await createProduct(payload);
        toast.success("Product created");
      }
      setModalOpen(false);
      getAdminProducts({ search: appliedSearch, page, limit: 10 })
        .then(setData)
        .catch(() => {});
    } catch (error) {
      toast.error(error.message || "Could not save product");
    }
  };

  const confirmDelete = async () => {
    try {
      await deleteProduct(deleting.id);
      toast.success(`“${deleting.name}” deleted`);
      setDeleting(null);
      getAdminProducts({ search: appliedSearch, page, limit: 10 })
        .then(setData)
        .catch(() => {});
    } catch (error) {
      toast.error(error.message || "Could not delete product");
      setDeleting(null);
    }
  };

  if (!data) return <LoadingSpinner label="Loading products…" />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900">Products</h1>
          <p className="text-sm text-slate-500">{data.total} products in the catalog</p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          + New product
        </button>
      </div>

      {/* Search */}
      <form
        className="flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          setPage(1);
          setAppliedSearch(search.trim());
        }}
      >
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search name, description or SKU…"
          className="h-11 w-full max-w-sm rounded-xl border border-slate-300 px-3 text-sm outline-none transition focus:border-brand-500"
        />
        <button
          type="submit"
          className="h-11 rounded-xl bg-slate-900 px-4 text-sm font-semibold text-white transition hover:bg-slate-700"
        >
          Search
        </button>
      </form>

      {data.items.length === 0 ? (
        <EmptyState
          icon="📦"
          title="No products found"
          description={appliedSearch ? `Nothing matches “${appliedSearch}”.` : "Add your first product."}
          actionLabel={appliedSearch ? "Clear search" : undefined}
          onAction={
            appliedSearch
              ? () => {
                  setSearch("");
                  setAppliedSearch("");
                  setPage(1);
                }
              : undefined
          }
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Product</th>
                  <th className="px-4 py-3">SKU</th>
                  <th className="px-4 py-3">Price</th>
                  <th className="px-4 py-3 text-center">Stock</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((product) => (
                  <tr key={product.id} className="transition hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <img
                          src={product.primary_image_url || IMAGE_FALLBACK}
                          alt=""
                          className="h-10 w-10 rounded-lg object-cover"
                          loading="lazy"
                        />
                        <div className="min-w-0">
                          <p className="truncate font-semibold text-slate-900">
                            {product.is_featured && (
                              <span title="Featured" className="mr-1">⭐</span>
                            )}
                            {product.name}
                          </p>
                          <p className="text-xs text-slate-400">{product.category_name ?? "Uncategorized"}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-500">{product.sku}</td>
                    <td className="px-4 py-3">
                      <span className="font-semibold text-slate-900">
                        {formatCurrency(product.sale_price ?? product.price)}
                      </span>
                      {product.sale_price != null && (
                        <span className="ml-1.5 text-xs text-slate-400 line-through">
                          {formatCurrency(product.price)}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <StockBadge stock={product.stock} />
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${
                          product.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-600"
                        }`}
                      >
                        {product.is_active ? "Active" : "Hidden"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => openEdit(product)}
                          className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-100"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeleting(product)}
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
        title={editing ? "Edit product" : "New product"}
        maxWidth="max-w-2xl"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="max-h-[70vh] overflow-y-auto pr-1">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label htmlFor="p-name" className={label}>Name *</label>
              <input
                id="p-name"
                className={`${input} ${errors.name ? "border-red-400" : ""}`}
                {...register("name", { required: "Name is required", minLength: 2 })}
              />
              {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
            </div>

            <div>
              <label htmlFor="p-sku" className={label}>SKU</label>
              <input id="p-sku" className={input} placeholder="Auto-generated when empty" {...register("sku")} />
            </div>

            <div>
              <label htmlFor="p-stock" className={label}>Stock *</label>
              <input
                id="p-stock"
                type="number"
                min="0"
                className={`${input} ${errors.stock ? "border-red-400" : ""}`}
                {...register("stock", {
                  required: "Stock is required",
                  min: { value: 0, message: "Cannot be negative" },
                  valueAsNumber: true,
                })}
              />
              {errors.stock && <p className="mt-1 text-xs text-red-600">{errors.stock.message}</p>}
            </div>

            <div>
              <label htmlFor="p-price" className={label}>Price ($) *</label>
              <input
                id="p-price"
                type="number"
                step="0.01"
                min="0.01"
                className={`${input} ${errors.price ? "border-red-400" : ""}`}
                {...register("price", {
                  required: "Price is required",
                  min: { value: 0.01, message: "Must be greater than 0" },
                })}
              />
              {errors.price && <p className="mt-1 text-xs text-red-600">{errors.price.message}</p>}
            </div>

            <div>
              <label htmlFor="p-sale" className={label}>Sale price ($)</label>
              <input
                id="p-sale"
                type="number"
                step="0.01"
                min="0"
                placeholder="Optional"
                className={`${input} ${errors.sale_price ? "border-red-400" : ""}`}
                {...register("sale_price", {
                  min: { value: 0, message: "Cannot be negative" },
                })}
              />
              {errors.sale_price && (
                <p className="mt-1 text-xs text-red-600">{errors.sale_price.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="p-category" className={label}>Category</label>
              <select id="p-category" className={input} {...register("category_id")}>
                <option value="">— None —</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="p-brand" className={label}>Brand</label>
              <select id="p-brand" className={input} {...register("brand_id")}>
                <option value="">— None —</option>
                {brands.map((brand) => (
                  <option key={brand.id} value={brand.id}>
                    {brand.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="p-image" className={label}>Image URL</label>
              <input
                id="p-image"
                type="url"
                placeholder="https://…"
                className={input}
                {...register("image_url")}
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="p-description" className={label}>Description</label>
              <textarea
                id="p-description"
                rows="3"
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-brand-500"
                {...register("description")}
              />
            </div>

            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input type="checkbox" className="h-4 w-4 accent-brand-600" {...register("is_active")} />
              Active (visible in store)
            </label>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input type="checkbox" className="h-4 w-4 accent-brand-600" {...register("is_featured")} />
              Featured (home page)
            </label>
          </div>

          <div className="mt-6 flex justify-end gap-3">
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
              {isSubmitting ? "Saving…" : editing ? "Save changes" : "Create product"}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(deleting)}
        title="Delete product?"
        message={`“${deleting?.name}” will be permanently removed. Past orders keep their snapshot.`}
        confirmLabel="Delete"
        danger
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(null)}
      />
    </div>
  );
}
