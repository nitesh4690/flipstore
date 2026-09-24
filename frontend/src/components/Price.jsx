import { formatCurrency } from "../utils/format.js";

/**
 * Price display: sale price highlighted, original struck through,
 * discount badge shown when a sale is active.
 */
export default function Price({ price, salePrice, size = "md", showBadge = true }) {
  const numericPrice = Number(price);
  const numericSale = salePrice !== null && salePrice !== undefined ? Number(salePrice) : null;
  const onSale = numericSale !== null && numericSale < numericPrice;

  const priceClasses = {
    sm: "text-base",
    md: "text-lg",
    lg: "text-3xl",
  };

  const discount = onSale
    ? Math.round((1 - numericSale / numericPrice) * 100)
    : 0;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className={`font-bold text-slate-900 ${priceClasses[size]}`}>
        {formatCurrency(onSale ? numericSale : numericPrice)}
      </span>
      {onSale && (
        <span className="text-sm text-slate-400 line-through">
          {formatCurrency(numericPrice)}
        </span>
      )}
      {onSale && showBadge && (
        <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-600">
          -{discount}%
        </span>
      )}
    </div>
  );
}
