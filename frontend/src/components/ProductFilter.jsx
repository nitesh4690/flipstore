import RatingStars from "./RatingStars.jsx";

/**
 * Filter sidebar: category, price range, brand, rating, availability.
 * Fully controlled — the page owns the active filters and URL state.
 */
export default function ProductFilter({ categories, brands, filters, onChange, onClear, activeCount = 0 }) {
  const section = "border-b border-slate-200 py-5";
  const heading = "text-sm font-bold uppercase tracking-wide text-slate-900";

  const radioRow = (label, checked, onClick, extra) => (
    <label
      key={label}
      className="flex cursor-pointer items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-sm text-slate-600 transition hover:bg-slate-50"
    >
      <span className="flex items-center gap-2">
        <input
          type="radio"
          checked={checked}
          onChange={onClick}
          className="h-4 w-4 border-slate-300 text-brand-600 accent-brand-600"
        />
        <span>{label}</span>
      </span>
      {extra}
    </label>
  );

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between pb-2">
        <h2 className="text-base font-bold text-slate-900">Filters</h2>
        <button
          type="button"
          onClick={onClear}
          disabled={activeCount === 0}
          className="text-xs font-semibold text-brand-600 transition hover:text-brand-700 disabled:opacity-40"
        >
          Clear all ({activeCount})
        </button>
      </div>

      {/* Category */}
      <section className={section}>
        <h3 className={heading}>Category</h3>
        <div className="mt-2 space-y-0.5">
          {radioRow("All categories", filters.category === "", () => onChange("category", ""))}
          {categories.map((category) =>
            radioRow(
              category.name,
              filters.category === category.slug,
              () => onChange("category", category.slug),
              <span className="text-xs text-slate-400">{category.product_count}</span>,
            ),
          )}
        </div>
      </section>

      {/* Price */}
      <section className={section}>
        <h3 className={heading}>Price range</h3>
        <div className="mt-3 flex items-center gap-2">
          <input
            type="number"
            min={0}
            inputMode="numeric"
            aria-label="Minimum price"
            placeholder="Min"
            value={filters.min_price}
            onChange={(event) => onChange("min_price", event.target.value, { defer: true })}
            className="h-9 w-full rounded-lg border border-slate-300 px-2 text-sm outline-none focus:border-brand-500"
          />
          <span className="text-slate-400">–</span>
          <input
            type="number"
            min={0}
            inputMode="numeric"
            aria-label="Maximum price"
            placeholder="Max"
            value={filters.max_price}
            onChange={(event) => onChange("max_price", event.target.value, { defer: true })}
            className="h-9 w-full rounded-lg border border-slate-300 px-2 text-sm outline-none focus:border-brand-500"
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {[
            ["Under $50", { min_price: "", max_price: "50" }],
            ["$50 – $100", { min_price: "50", max_price: "100" }],
            ["$100+", { min_price: "100", max_price: "" }],
          ].map(([label, range]) => (
            <button
              key={label}
              type="button"
              onClick={() => {
                onChange("min_price", range.min_price);
                onChange("max_price", range.max_price);
              }}
              className="rounded-full border border-slate-300 px-3 py-1 text-xs font-medium text-slate-600 transition hover:border-brand-500 hover:text-brand-600"
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      {/* Brand */}
      <section className={section}>
        <h3 className={heading}>Brand</h3>
        <div className="mt-2 max-h-52 space-y-0.5 overflow-y-auto">
          {radioRow("All brands", filters.brand === "", () => onChange("brand", ""))}
          {brands.map((brand) =>
            radioRow(
              brand.name,
              filters.brand === brand.slug,
              () => onChange("brand", brand.slug),
              <span className="text-xs text-slate-400">{brand.product_count}</span>,
            ),
          )}
        </div>
      </section>

      {/* Rating */}
      <section className={section}>
        <h3 className={heading}>Rating</h3>
        <div className="mt-2 space-y-0.5">
          {radioRow("Any rating", filters.min_rating === "", () => onChange("min_rating", ""))}
          {[4, 3, 2].map((value) =>
            radioRow(
              `${value} & up`,
              filters.min_rating === String(value),
              () => onChange("min_rating", String(value)),
              <RatingStars value={value} size="text-xs" />,
            ),
          )}
        </div>
      </section>

      {/* Availability */}
      <section className="pt-5">
        <h3 className={heading}>Availability</h3>
        <div className="mt-2 space-y-0.5">
          {radioRow("Any", filters.in_stock === "", () => onChange("in_stock", ""))}
          {radioRow("In stock", filters.in_stock === "true", () => onChange("in_stock", "true"))}
          {radioRow("Out of stock", filters.in_stock === "false", () => onChange("in_stock", "false"))}
        </div>
      </section>
    </div>
  );
}
