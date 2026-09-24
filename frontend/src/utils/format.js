/** Formatting helpers shared across the storefront. */

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export function formatCurrency(amount) {
  return currencyFormatter.format(Number(amount) || 0);
}

export function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}

export function ratingLabel(rating) {
  const value = Number(rating) || 0;
  if (value >= 4.5) return "Excellent";
  if (value >= 4) return "Very good";
  if (value >= 3) return "Average";
  if (value > 0) return "Below average";
  return "No ratings yet";
}

/** Neutral SVG fallback when a product image fails to load. */
export const IMAGE_FALLBACK = `data:image/svg+xml,${encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600"><rect width="100%" height="100%" fill="#e2e8f0"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#94a3b8" font-family="sans-serif" font-size="26">No image</text></svg>',
)}`;
