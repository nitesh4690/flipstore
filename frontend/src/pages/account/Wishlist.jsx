import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import EmptyState from "../../components/EmptyState.jsx";
import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import ProductCard from "../../components/ProductCard.jsx";
import { useToast } from "../../context/ToastContext.jsx";
import useDocumentTitle from "../../hooks/useDocumentTitle.js";
import { getWishlist } from "../../services/shop.js";

/** Saved products grid (server snapshots). */
export default function Wishlist() {
  useDocumentTitle("My wishlist");
  const toast = useToast();
  const navigate = useNavigate();
  const [items, setItems] = useState(null); // null = loading

  const load = () =>
    getWishlist()
      .then((payload) => setItems(payload.items))
      .catch((error) => {
        setItems([]);
        toast.error(error.message || "Could not load your wishlist");
      });

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (items === null) return <LoadingSpinner label="Loading your wishlist…" />;

  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <EmptyState
          icon="❤️"
          title="Your wishlist is empty"
          description="Tap the heart on any product to save it for later."
          actionLabel="Browse products"
          onAction={() => navigate("/products")}
        />
      </div>
    );
  }

  return (
    <section>
      <h2 className="mb-4 text-lg font-bold text-slate-900">
        Saved products <span className="text-sm font-medium text-slate-400">({items.length})</span>
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((entry) => (
          <ProductCard key={entry.id} product={entry.product} />
        ))}
      </div>
    </section>
  );
}
