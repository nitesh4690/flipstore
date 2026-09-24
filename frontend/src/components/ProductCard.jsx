import { Link } from "react-router-dom";

import { useCart } from "../context/CartContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { useWishlist } from "../context/WishlistContext.jsx";
import { IMAGE_FALLBACK, formatCurrency } from "../utils/format.js";
import Price from "./Price.jsx";
import RatingStars from "./RatingStars.jsx";

/**
 * Product card for grid listings: image, wishlist toggle,
 * rating, price/sale, stock status and add-to-cart.
 */
export default function ProductCard({ product }) {
  const { addItem } = useCart();
  const { toggle, has } = useWishlist();
  const toast = useToast();
  const wishlisted = has(product.id);

  const handleAddToCart = async (event) => {
    event.preventDefault(); // don't navigate when clicking inside the card link
    if (!product.in_stock) {
      toast.error("This product is out of stock");
      return;
    }
    try {
      await addItem(product, 1);
      toast.success(`Added “${product.name}” to cart`);
    } catch (error) {
      toast.error(error.message || "Could not add to cart");
    }
  };

  const handleWishlist = async (event) => {
    event.preventDefault();
    try {
      const added = await toggle(product.id);
      toast.info(added ? "Saved to wishlist" : "Removed from wishlist");
    } catch (error) {
      toast.error(error.message || "Could not update wishlist");
    }
  };

  return (
    <article className="group relative flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-lg">
      <Link
        to={`/products/${product.slug}`}
        className="block"
        aria-label={`View ${product.name}`}
      >
        <div className="relative aspect-square overflow-hidden bg-slate-100">
          <img
            src={product.primary_image_url || IMAGE_FALLBACK}
            alt={product.name}
            loading="lazy"
            onError={(event) => {
              event.currentTarget.src = IMAGE_FALLBACK;
            }}
            className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
          />
          {product.discount_percent > 0 && (
            <span className="absolute left-3 top-3 rounded-full bg-red-600 px-2.5 py-1 text-xs font-bold text-white shadow">
              -{product.discount_percent}%
            </span>
          )}
          {!product.in_stock && (
            <span className="absolute inset-x-0 bottom-0 bg-slate-900/70 py-1.5 text-center text-xs font-semibold text-white">
              Out of stock
            </span>
          )}
        </div>
      </Link>

      <button
        type="button"
        onClick={handleWishlist}
        aria-pressed={wishlisted}
        aria-label={wishlisted ? "Remove from wishlist" : "Add to wishlist"}
        className={`absolute right-3 top-3 grid h-9 w-9 place-items-center rounded-full shadow transition ${
          wishlisted
            ? "bg-red-500 text-white"
            : "bg-white/90 text-slate-500 hover:bg-white hover:text-red-500"
        }`}
      >
        {wishlisted ? "♥" : "♡"}
      </button>

      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium uppercase tracking-wide text-slate-400">
            {product.category_name ?? "General"}
          </span>
          {product.brand_name && (
            <span className="font-semibold text-slate-500">{product.brand_name}</span>
          )}
        </div>

        <Link
          to={`/products/${product.slug}`}
          className="line-clamp-2 min-h-11 text-sm font-semibold text-slate-900 transition hover:text-brand-600"
        >
          {product.name}
        </Link>

        <RatingStars value={product.rating} count={product.rating_count} size="text-sm" />

        <div className="mt-auto flex items-end justify-between gap-2 pt-1">
          <Price price={product.price} salePrice={product.sale_price} size="sm" />
          <span
            className={`text-xs font-medium ${
              product.in_stock ? "text-emerald-600" : "text-slate-400"
            }`}
          >
            {product.in_stock ? "In stock" : "Sold out"}
          </span>
        </div>

        <button
          type="button"
          onClick={handleAddToCart}
          disabled={!product.in_stock}
          className="mt-2 w-full rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          Add to cart · {formatCurrency(product.effective_price)}
        </button>
      </div>
    </article>
  );
}
