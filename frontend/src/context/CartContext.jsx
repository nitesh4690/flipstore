import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "./AuthContext.jsx";
import {
  addToCart as apiAddToCart,
  applyCoupon as apiApplyCoupon,
  clearServerCart,
  getCart,
  removeCartItem as apiRemoveItem,
  updateCartQuantity as apiUpdateQuantity,
} from "../services/shop.js";

const CartContext = createContext(null);
const STORAGE_KEY = "flipstore_cart";

/* Totals rules mirrored from the backend (guest carts are computed locally). */
const TAX_RATE = 0.08;
const FREE_SHIPPING_THRESHOLD = 75;
const SHIPPING = { standard: 9.99, express: 19.99, pickup: 0 };

const round2 = (value) => Math.round((Number(value) + Number.EPSILON) * 100) / 100;

function readLocal() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/** Server cart envelope -> the shape the Cart page already consumes. */
function fromServerCart(cart) {
  return {
    items: cart.items.map((item) => ({
      key: item.id, // server item id doubles as the React key / update handle
      id: item.product_id,
      productId: item.product_id,
      variantId: item.variant_id,
      name: item.name,
      slug: item.slug,
      image: item.image,
      price: item.unit_price,
      quantity: item.quantity,
      maxStock: item.stock_available,
      variantName: item.variant_name,
    })),
    totals: cart.totals,
    couponCode: cart.totals.coupon_code,
  };
}

function guestTotals(items, method = "standard") {
  const subtotal = round2(items.reduce((sum, item) => sum + item.price * item.quantity, 0));
  const discount = 0;
  const shipping =
    method === "pickup" ? 0 : method === "express" ? SHIPPING.express
    : subtotal >= FREE_SHIPPING_THRESHOLD ? 0 : SHIPPING.standard;
  const tax = round2((subtotal - discount) * TAX_RATE);
  return {
    subtotal,
    discount,
    shipping,
    tax,
    total: round2(subtotal - discount + shipping + tax),
    shipping_method: method,
    coupon_code: null,
    free_shipping_threshold_met: subtotal >= FREE_SHIPPING_THRESHOLD && method === "standard",
  };
}

export function CartProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [items, setItems] = useState(readLocal);
  const [couponCode, setCouponCode] = useState(null);
  const [totals, setTotals] = useState(() => guestTotals(readLocal()));
  const [syncing, setSyncing] = useState(false);
  // Guard against StrictMode double-effects pushing local items twice.
  const syncedForAuth = useRef(false);

  const persistLocal = (next) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setItems(next);
    setTotals(guestTotals(next));
    setCouponCode(null);
  };

  /* On login: merge the guest cart into the server cart, then hydrate. */
  useEffect(() => {
    if (isAuthenticated === syncedForAuth.current) return;
    syncedForAuth.current = isAuthenticated;

    if (isAuthenticated) {
      (async () => {
        setSyncing(true);
        try {
          const local = readLocal();
          let cart = null;
          for (const item of local) {
            try {
              cart = await apiAddToCart({
                product_id: item.id,
                variant_id: item.variantId ?? null,
                quantity: item.quantity,
              });
            } catch {
              // Skip lines that became unavailable (e.g. sold out) on merge.
            }
          }
          cart = cart ?? (await getCart());
          const normalized = fromServerCart(cart);
          setItems(normalized.items);
          setTotals(normalized.totals);
          setCouponCode(normalized.couponCode);
          localStorage.removeItem(STORAGE_KEY);
        } catch {
          /* stay on whatever we have; actions will surface API errors */
        } finally {
          setSyncing(false);
        }
      })();
    } else {
      // Logged out: the server cart stays server-side; resume the local one.
      const local = readLocal();
      setItems(local);
      setTotals(guestTotals(local));
      setCouponCode(null);
    }
  }, [isAuthenticated]);

  /* Local persistence for guest carts only. */
  useEffect(() => {
    if (!isAuthenticated) localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  }, [items, isAuthenticated]);

  const applyServer = useCallback((cart, message) => {
    const normalized = fromServerCart(cart);
    setItems(normalized.items);
    setTotals(normalized.totals);
    setCouponCode(normalized.couponCode);
    return message;
  }, []);

  const addItem = useCallback(
    async (product, quantity = 1, variant = null) => {
      if (isAuthenticated) {
        const cart = await apiAddToCart({
          product_id: product.id,
          variant_id: variant?.id ?? null,
          quantity,
        });
        return applyServer(cart);
      }
      // Guest: merge into local lines (price snapshot from the card/detail page)
      const key = `${product.id}:${variant?.id ?? ""}`;
      const stock = variant ? variant.stock : product.stock;
      const next = [...readLocal()];
      const existing = next.find((item) => item.key === key);
      if (existing) {
        existing.quantity = Math.min(existing.quantity + quantity, stock || 99);
      } else {
        next.push({
          key,
          id: product.id,
          variantId: variant?.id ?? null,
          name: product.name,
          slug: product.slug,
          image: product.primary_image_url,
          price: variant?.price ?? product.effective_price,
          quantity: Math.min(quantity, stock || 99),
          maxStock: stock || 99,
          variantName: variant?.name ?? null,
        });
      }
      persistLocal(next);
    },
    [isAuthenticated, applyServer],
  );

  const updateQuantity = useCallback(
    async (key, quantity) => {
      if (isAuthenticated) {
        const cart = await apiUpdateQuantity(key, quantity);
        return applyServer(cart);
      }
      const next = readLocal()
        .map((item) =>
          item.key === key
            ? { ...item, quantity: Math.max(1, Math.min(quantity, item.maxStock)) }
            : item,
        )
        .filter((item) => item.quantity > 0);
      persistLocal(next);
    },
    [isAuthenticated, applyServer],
  );

  const removeItem = useCallback(
    async (key) => {
      if (isAuthenticated) {
        const cart = await apiRemoveItem(key);
        return applyServer(cart);
      }
      persistLocal(readLocal().filter((item) => item.key !== key));
    },
    [isAuthenticated, applyServer],
  );

  const clearCart = useCallback(async () => {
    if (isAuthenticated) {
      const cart = await clearServerCart();
      return applyServer(cart);
    }
    persistLocal([]);
  }, [isAuthenticated, applyServer]);

  const applyCoupon = useCallback(
    async (code) => {
      if (!isAuthenticated) throw new Error("Sign in to apply coupon codes");
      const cart = await apiApplyCoupon(code);
      return applyServer(cart, code ? `Coupon ${cart.totals.coupon_code} applied` : "Coupon removed");
    },
    [isAuthenticated, applyServer],
  );

  const value = useMemo(
    () => ({
      items,
      totals,
      couponCode,
      syncing,
      isServerCart: isAuthenticated,
      count: items.reduce((sum, item) => sum + item.quantity, 0),
      subtotal: totals?.subtotal ?? 0,
      addItem,
      updateQuantity,
      removeItem,
      clearCart,
      applyCoupon,
    }),
    [
      items,
      totals,
      couponCode,
      syncing,
      isAuthenticated,
      addItem,
      updateQuantity,
      removeItem,
      clearCart,
      applyCoupon,
    ],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) throw new Error("useCart must be used within CartProvider");
  return context;
}
