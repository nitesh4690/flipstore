import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import LoadingSpinner from "../components/LoadingSpinner.jsx";
import Pagination from "../components/Pagination.jsx";
import ProductFilter from "../components/ProductFilter.jsx";
import ProductGrid from "../components/ProductGrid.jsx";
import useDocumentTitle from "../hooks/useDocumentTitle.js";
import { useToast } from "../context/ToastContext.jsx";
import { fetchBrands, fetchCategories, fetchProducts } from "../services/catalog.js";

const SORT_OPTIONS = [
  ["newest", "Newest first"],
  ["price_asc", "Price: low to high"],
  ["price_desc", "Price: high to low"],
  ["rating", "Top rated"],
  ["popular", "Most popular"],
  ["name_asc", "Name: A–Z"],
];

const FILTER_KEYS = ["search", "category", "brand", "min_price", "max_price", "min_rating", "in_stock", "is_featured"];

/**
 * Product listing page. All filter/sort/page state lives in the URL so it is
 * shareable and survives reloads.
 */
export default function Products() {
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState([]);
  const [brands, setBrands] = useState([]);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  // Mirror of searchParams so rapid sequential updates don't clobber each other.
  const paramsRef = useRef(new URLSearchParams(searchParams));
  useEffect(() => {
    paramsRef.current = new URLSearchParams(searchParams);
  }, [searchParams]);
  const debounceRef = useRef({});

  const filters = {
    search: searchParams.get("search") ?? "",
    category: searchParams.get("category") ?? "",
    brand: searchParams.get("brand") ?? "",
    min_price: searchParams.get("min_price") ?? "",
    max_price: searchParams.get("max_price") ?? "",
    min_rating: searchParams.get("min_rating") ?? "",
    in_stock: searchParams.get("in_stock") ?? "",
    is_featured: searchParams.get("is_featured") ?? "",
    sort: searchParams.get("sort") ?? "newest",
    page: Number(searchParams.get("page") ?? 1),
  };

  useDocumentTitle(filters.search ? `Search: ${filters.search}` : "Shop");

  const applyParams = useCallback((mutate) => {
    const next = new URLSearchParams(paramsRef.current);
    mutate(next);
    paramsRef.current = next;
    setSearchParams(next, { replace: true });
  }, [setSearchParams]);

  const setFilter = useCallback(
    (key, value, options = {}) => {
      const apply = () =>
        applyParams((params) => {
          if (value === "" || value === null || value === undefined) params.delete(key);
          else params.set(key, value);
          if (key !== "page" && key !== "sort") params.delete("page");
        });

      clearTimeout(debounceRef.current[key]);
      if (options.defer) debounceRef.current[key] = setTimeout(apply, 500);
      else apply();
    },
    [applyParams],
  );

  const clearFilters = useCallback(() => {
    const keepSort = paramsRef.current.get("sort");
    const next = new URLSearchParams();
    if (keepSort) next.set("sort", keepSort);
    paramsRef.current = next;
    setSearchParams(next, { replace: true });
  }, [setSearchParams]);

  const activeCount = FILTER_KEYS.filter((key) => filters[key] !== "" && filters[key] !== false).length;

  // Data fetching (depends on the serialized query string)
  const query = searchParams.toString();
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchProducts({
      search: filters.search,
      category: filters.category,
      brand: filters.brand,
      min_price: filters.min_price,
      max_price: filters.max_price,
      min_rating: filters.min_rating,
      in_stock: filters.in_stock === "" ? "" : filters.in_stock === "true",
      is_featured: filters.is_featured === "" ? "" : filters.is_featured === "true",
      sort: filters.sort,
      page: filters.page,
      limit: 12,
    })
      .then((result) => !cancelled && setData(result))
      .catch((error) => {
        if (!cancelled) {
          setData(null);
          toast.error(error.message || "Failed to load products");
        }
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  // Sidebar taxonomy (fetched once)
  useEffect(() => {
    fetchCategories()
      .then((rows) => setCategories(rows.filter((row) => row.parent_id === null)))
      .catch(() => setCategories([]));
    fetchBrands()
      .then(setBrands)
      .catch(() => setBrands([]));
  }, []);

  const filterPanel = (
    <ProductFilter
      categories={categories}
      brands={brands}
      filters={filters}
      onChange={setFilter}
      onClear={clearFilters}
      activeCount={activeCount}
    />
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">
          {filters.search ? `Results for “${filters.search}”` : "All products"}
        </h1>
        <p className="mt-1 text-sm text-slate-500" aria-live="polite">
          {loading ? "Loading…" : `${data?.total ?? 0} products found`}
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[280px_1fr]">
        {/* Desktop sidebar */}
        <aside className="hidden lg:block">
          <div className="sticky top-32">{filterPanel}</div>
        </aside>

        {/* Mobile filter drawer */}
        {mobileFiltersOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <div
              className="absolute inset-0 bg-slate-900/50"
              onClick={() => setMobileFiltersOpen(false)}
              aria-hidden
            />
            <div className="absolute inset-y-0 left-0 w-full max-w-sm overflow-y-auto bg-white p-4 shadow-xl">
              <div className="mb-3 flex items-center justify-between">
                <span className="font-bold">Filters</span>
                <button
                  type="button"
                  aria-label="Close filters"
                  onClick={() => setMobileFiltersOpen(false)}
                  className="grid h-9 w-9 place-items-center rounded-lg bg-slate-100"
                >
                  ✕
                </button>
              </div>
              {filterPanel}
              <button
                type="button"
                onClick={() => setMobileFiltersOpen(false)}
                className="mt-4 w-full rounded-xl bg-brand-600 py-3 text-sm font-semibold text-white"
              >
                Show {data?.total ?? 0} results
              </button>
            </div>
          </div>
        )}

        <div>
          {/* Toolbar */}
          <div className="mb-5 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileFiltersOpen(true)}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 lg:hidden"
            >
              ☰ Filters{activeCount > 0 ? ` (${activeCount})` : ""}
            </button>

            <div className="ml-auto flex items-center gap-2">
              <label htmlFor="sort-select" className="text-sm text-slate-500">
                Sort by
              </label>
              <select
                id="sort-select"
                value={filters.sort}
                onChange={(event) => setFilter("sort", event.target.value)}
                className="h-10 rounded-xl border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 outline-none transition focus:border-brand-500"
              >
                {SORT_OPTIONS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Active filter chips */}
          {activeCount > 0 && (
            <div className="mb-5 flex flex-wrap gap-2">
              {FILTER_KEYS.filter((key) => filters[key] !== "" && filters[key] !== false).map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setFilter(key, "")}
                  className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700 transition hover:bg-brand-100"
                >
                  {key === "search" ? `“${filters.search}”` : `${key.replace("_", " ")}: ${filters[key]}`}
                  <span aria-hidden>✕</span>
                </button>
              ))}
            </div>
          )}

          {loading && !data ? (
            <LoadingSpinner label="Loading products…" />
          ) : (
            <ProductGrid
              products={data?.items ?? []}
              loading={loading}
              emptyTitle={filters.search ? `No results for “${filters.search}”` : "No products found"}
              emptyDescription="Try different keywords or clear your filters."
              emptyAction={{ label: "Clear filters", onClick: clearFilters }}
            />
          )}

          <Pagination
            page={data?.page ?? 1}
            totalPages={data?.total_pages ?? 0}
            onPageChange={(page) => setFilter("page", String(page))}
          />
        </div>
      </div>
    </div>
  );
}
