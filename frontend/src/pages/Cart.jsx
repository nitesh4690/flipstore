import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import ConfirmDialog from "../components/ConfirmDialog.jsx";
import EmptyState from "../components/EmptyState.jsx";
import QuantitySelector from "../components/QuantitySelector.jsx";
import { useCart } from "../context/CartContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import useDocumentTitle from "../hooks/useDocumentTitle.js";
import { IMAGE_FALLBACK, formatCurrency } from "../utils/format.js";

/**
 * Shopping cart. Server-side when signed in (coupons, real totals);
 * local-storage cart for guests with estimated totals.
 */
export default function Cart() {
  useDocumentTitle("Cart");
  const {
    items,
    totals,
    couponCode,
    updateQuantity,
    removeItem,
    clearCart,
    applyCoupon,
  } = useCart();
  const toast = useToast();
  const navigate = useNavigate();
  const [confirmClearOpen, setConfirmClearOpen] = useState(false);
  const [pendingRemoval, setPendingRemoval] = useState(null);
  const [couponInput, setCouponInput] = useState("");
  const [couponBusy, setCouponBusy] = useState(false);

  if (items.length === 0) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <EmptyState
          icon="🛒"
          title="Your cart is empty"
          description="Browse the catalog and add products to your cart — they'll show up here."
          actionLabel="Start shopping"
          onAction={() => navigate("/products")}
        />
      </div>
    );
  }

  const handleQuantity = async (key, quantity) => {
    try {
      await updateQuantity(key, quantity);
    } catch (error) {
      toast.error(error.message || "Could not update quantity");
    }
  };

  const confirmRemove = async () => {
    try {
      await removeItem(pendingRemoval.key);
      toast.info("Item removed from cart");
    } catch (error) {
      toast.error(error.message || "Could not remove item");
    }
    setPendingRemoval(null);
  };

  const handleClear = async () => {
    try {
      await clearCart();
      toast.info("Cart cleared");
    } catch (error) {
      toast.error(error.message || "Could not clear cart");
    }
    setConfirmClearOpen(false);
  };

  const handleCoupon = async (event) => {
    event.preventDefault();
    const code = couponInput.trim();
    if (!code) return;
    setCouponBusy(true);
    try {
      const message = await applyCoupon(code.toUpperCase());
      toast.success(message || "Coupon applied");
      setCouponInput("");
    } catch (error) {
      toast.error(error.message || "Could not apply coupon");
    } finally {
      setCouponBusy(false);
    }
  };

  const handleRemoveCoupon = async () => {
    try {
      const message = await applyCoupon(null);
      toast.info(message || "Coupon removed");
      setCouponInput("");
    } catch (error) {
      toast.error(error.message || "Could not remove coupon");
    }
  };

  const shippingLine =
    totals.shipping === 0
      ? "FREE"
      : formatCurrency(totals.shipping);
  const freeShippingGap = Math.max(0, 75 - totals.subtotal);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-extrabold text-slate-900">Shopping cart</h1>
        <button
          type="button"
          onClick={() => setConfirmClearOpen(true)}
          className="text-sm font-semibold text-red-500 transition hover:text-red-600"
        >
          Clear cart
        </button>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          {items.map((item) => (
            <article
              key={item.key}
              className="flex gap-4 rounded-2xl border border-slate-200 bg-white p-4"
            >
              <Link
                to={`/products/${item.slug}`}
                className="h-24 w-24 shrink-0 overflow-hidden rounded-xl bg-slate-100"
              >
                <img
                  src={item.image || IMAGE_FALLBACK}
                  alt={item.name}
                  onError={(event) => {
                    event.currentTarget.src = IMAGE_FALLBACK;
                  }}
                  className="h-full w-full object-cover"
                />
              </Link>

              <div className="flex flex-1 flex-col">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <Link
                      to={`/products/${item.slug}`}
                      className="line-clamp-2 text-sm font-semibold text-slate-900 hover:text-brand-600"
                    >
                      {item.name}
                    </Link>
                    {item.variantName && (
                      <p className="mt-0.5 text-xs text-slate-500">{item.variantName}</p>
                    )}
                    <p className="mt-1 text-sm font-bold text-slate-900">
                      {formatCurrency(item.price)}
                    </p>
                  </div>
                  <button
                    type="button"
                    aria-label={`Remove ${item.name} from cart`}
                    onClick={() => setPendingRemoval(item)}
                    className="text-slate-400 transition hover:text-red-500"
                  >
                    ✕
                  </button>
                </div>

                <div className="mt-auto flex items-center justify-between gap-3 pt-3">
                  <QuantitySelector
                    value={item.quantity}
                    max={item.maxStock}
                    onChange={(quantity) => handleQuantity(item.key, quantity)}
                    id={`qty-${item.key}`}
                  />
                  <span className="text-sm font-bold text-slate-900">
                    {formatCurrency(item.price * item.quantity)}
                  </span>
                </div>
              </div>
            </article>
          ))}

          {freeShippingGap > 0 && (
            <p className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              🚚 Add <strong>{formatCurrency(freeShippingGap)}</strong> more for free
              standard shipping
            </p>
          )}
        </div>

        {/* Summary */}
        <aside className="h-fit rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="text-base font-bold text-slate-900">Order summary</h2>

          {/* Coupon */}
          <form onSubmit={handleCoupon} className="mt-4 flex gap-2">
            <label htmlFor="coupon-code" className="sr-only">
              Coupon code
            </label>
            <input
              id="coupon-code"
              type="text"
              value={couponInput}
              onChange={(event) => setCouponInput(event.target.value.toUpperCase())}
              placeholder="Coupon code"
              className="h-10 w-full rounded-xl border border-slate-300 px-3 text-sm uppercase outline-none focus:border-brand-500"
            />
            <button
              type="submit"
              disabled={couponBusy || !couponInput.trim()}
              className="h-10 shrink-0 rounded-xl bg-slate-900 px-4 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50"
            >
              {couponBusy ? "…" : "Apply"}
            </button>
          </form>
          <p className="mt-1.5 text-xs text-slate-400">
            Try <strong>WELCOME10</strong>, <strong>SAVE20</strong> or{" "}
            <strong>FLAT15</strong>
          </p>

          <dl className="mt-5 space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">Subtotal</dt>
              <dd className="font-semibold text-slate-900">
                {formatCurrency(totals.subtotal)}
              </dd>
            </div>
            {totals.discount > 0 && (
              <div className="flex justify-between text-emerald-600">
                <dt className="flex items-center gap-2">
                  Discount
                  <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-bold">
                    {couponCode}
                  </span>
                  <button
                    type="button"
                    onClick={handleRemoveCoupon}
                    className="text-xs underline text-slate-400 hover:text-red-500"
                  >
                    remove
                  </button>
                </dt>
                <dd className="font-semibold">−{formatCurrency(totals.discount)}</dd>
              </div>
            )}
            <div className="flex justify-between">
              <dt className="text-slate-500">Shipping (standard)</dt>
              <dd className="font-semibold text-slate-900">{shippingLine}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Estimated tax</dt>
              <dd className="font-semibold text-slate-900">{formatCurrency(totals.tax)}</dd>
            </div>
            <div className="border-t border-slate-200 pt-3 text-base">
              <div className="flex justify-between">
                <dt className="font-bold text-slate-900">Total</dt>
                <dd className="font-extrabold text-slate-900">
                  {formatCurrency(totals.total)}
                </dd>
              </div>
            </div>
          </dl>

          <button
            type="button"
            onClick={() => navigate("/checkout")}
            className="mt-6 w-full rounded-xl bg-brand-600 py-3 font-semibold text-white transition hover:bg-brand-700"
          >
            Proceed to checkout
          </button>
          <Link
            to="/products"
            className="mt-3 block w-full rounded-xl border border-slate-300 py-3 text-center text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            Continue shopping
          </Link>
          <p className="mt-4 text-center text-xs text-slate-400">
            🔒 Secure checkout · 30-day returns
          </p>
        </aside>
      </div>

      <ConfirmDialog
        open={confirmClearOpen}
        title="Clear cart?"
        message="All items will be removed from your shopping cart."
        confirmLabel="Clear cart"
        danger
        onConfirm={handleClear}
        onCancel={() => setConfirmClearOpen(false)}
      />

      <ConfirmDialog
        open={Boolean(pendingRemoval)}
        title="Remove item?"
        message={pendingRemoval ? `Remove “${pendingRemoval.name}” from your cart?` : ""}
        confirmLabel="Remove"
        danger
        onConfirm={confirmRemove}
        onCancel={() => setPendingRemoval(null)}
      />
    </div>
  );
}
