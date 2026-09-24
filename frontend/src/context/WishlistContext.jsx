import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "./AuthContext.jsx";
import {
  addWishlistItem,
  getWishlist,
  removeWishlistItem,
} from "../services/shop.js";

const WishlistContext = createContext(null);
const STORAGE_KEY = "flipstore_wishlist";

function readLocal() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function idsFrom(payload) {
  return (payload?.items ?? []).map((entry) => entry.product.id);
}

/**
 * Wishlist ids (enough for the heart buttons). Full product snapshots for the
 * account page come from getWishlist() when logged in.
 */
export function WishlistProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [ids, setIds] = useState(readLocal);
  const syncedForAuth = useRef(false);

  useEffect(() => {
    if (isAuthenticated === syncedForAuth.current) return;
    syncedForAuth.current = isAuthenticated;

    if (isAuthenticated) {
      (async () => {
        try {
          const local = readLocal();
          for (const productId of local) {
            try {
              await addWishlistItem(productId); // server ignores duplicates
            } catch {
              /* product may have been removed */
            }
          }
          setIds(idsFrom(await getWishlist()));
          localStorage.removeItem(STORAGE_KEY);
        } catch {
          /* keep current state; actions surface API errors */
        }
      })();
    } else {
      setIds(readLocal());
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  }, [ids, isAuthenticated]);

  const toggle = useCallback(
    async (productId) => {
      const had = ids.includes(productId);
      if (isAuthenticated) {
        const payload = had
          ? await removeWishlistItem(productId)
          : await addWishlistItem(productId);
        setIds(idsFrom(payload));
        return !had;
      }
      setIds((current) =>
        had ? current.filter((id) => id !== productId) : [...current, productId],
      );
      return !had;
    },
    [ids, isAuthenticated],
  );

  const has = useCallback((productId) => ids.includes(productId), [ids]);

  const value = useMemo(() => ({ ids, count: ids.length, toggle, has }), [ids, toggle, has]);
  return <WishlistContext.Provider value={value}>{children}</WishlistContext.Provider>;
}

export function useWishlist() {
  const context = useContext(WishlistContext);
  if (!context) throw new Error("useWishlist must be used within WishlistProvider");
  return context;
}
