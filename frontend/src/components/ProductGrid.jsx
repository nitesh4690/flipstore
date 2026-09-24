import EmptyState from "./EmptyState.jsx";
import ProductCard from "./ProductCard.jsx";
import { ProductGridSkeleton } from "./Skeleton.jsx";

/** Responsive product grid with loading skeleton and empty state. */
export default function ProductGrid({ products, loading = false, emptyTitle, emptyDescription, emptyAction }) {
  if (loading) return <ProductGridSkeleton count={8} />;

  if (!products || products.length === 0) {
    return (
      <EmptyState
        icon="🛍️"
        title={emptyTitle ?? "No products found"}
        description={emptyDescription ?? "Try adjusting your search or filters."}
        actionLabel={emptyAction?.label}
        onAction={emptyAction?.onClick}
      />
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-3 xl:grid-cols-4">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}
