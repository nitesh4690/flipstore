import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import EmptyState from "../components/EmptyState.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import Price from "../components/Price.jsx";
import ProductCard from "../components/ProductCard.jsx";
import QuantitySelector from "../components/QuantitySelector.jsx";
import RatingStars from "../components/RatingStars.jsx";
import ReviewSection from "../components/ReviewSection.jsx";
import { ProductGridSkeleton } from "../components/Skeleton.jsx";
import { useCart } from "../context/CartContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { useWishlist } from "../context/WishlistContext.jsx";
import useDocumentTitle from "../hooks/useDocumentTitle.js";
import { fetchProduct, fetchRelated } from "../services/catalog.js";
import { IMAGE_FALLBACK, formatCurrency, formatDate } from "../utils/format.js";

export default function ProductDetail() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { addItem } = useCart();
  const { toggle, has } = useWishlist();

  const [product, setProduct] = useState(null);
  const [related, setRelated] = useState([]);
  const [relatedLoaded, setRelatedLoaded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [imageIndex, setImageIndex] = useState(0);
  const [quantity, setQuantity] = useState(1);
  const [selectedVariantId, setSelectedVariantId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setProduct(null);
    setImageIndex(0);
    setQuantity(1);
    setSelectedVariantId(null);
    setRelated([]);
    setRelatedLoaded(false);

    fetchProduct(slug)
      .then(async (data) => {
        if (cancelled) return;
        setProduct(data);
        // Default-select the first in-stock variant when variants exist
        const firstAvailable = data.variants?.find((variant) => variant.stock > 0);
        setSelectedVariantId(firstAvailable?.id ?? data.variants?.[0]?.id ?? null);
        try {
          const rows = await fetchRelated(slug);
          if (!cancelled) setRelated(rows);
        } catch {
          if (!cancelled) setRelated([]);
        } finally {
          if (!cancelled) setRelatedLoaded(true);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setProduct(null);
          toast.error(error.message || "Product not found");
        }
      })
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  useDocumentTitle(product?.name ?? "Product");

  const selectedVariant = useMemo(
    () => product?.variants?.find((variant) => variant.id === selectedVariantId) ?? null,
    [product, selectedVariantId],
  );

  if (loading) return <LoadingSpinner label="Loading product…" />;
  if (!product) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <EmptyState
          icon="🤔"
          title="Product not found"
          description="The product you're looking for may have been removed or the link is incorrect."
          actionLabel="Back to products"
          onAction={() => navigate("/products")}
        />
      </div>
    );
  }

  const images = product.images.length
    ? product.images
    : [{ url: IMAGE_FALLBACK, alt_text: product.name }];

  const currentPrice = selectedVariant?.price ?? product.effective_price;
  const currentStock = selectedVariant ? selectedVariant.stock : product.stock;
  const inStock = currentStock > 0;
  const wishlisted = has(product.id);

  const handleAddToCart = () => {
    if (!inStock) {
      toast.error("This product is out of stock");
      return null;
    }
    if (selectedVariant && selectedVariant.stock < quantity) {
      toast.error(`Only ${selectedVariant.stock} left in stock`);
      return null;
    }
    return addItem(product, quantity, selectedVariant)
      .then(() => toast.success(`Added ${quantity} × “${product.name}” to cart`))
      .catch((error) => {
        toast.error(error.message || "Could not add to cart");
        throw error;
      });
  };

  const handleBuyNow = async () => {
    try {
      await handleAddToCart();
    } catch {
      return; // add failed — stay on the page
    }
    navigate("/checkout");
  };

  const handleWishlist = async () => {
    try {
      const added = await toggle(product.id);
      toast.info(added ? "Saved to wishlist" : "Removed from wishlist");
    } catch (error) {
      toast.error(error.message || "Could not update wishlist");
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb" className="mb-6 text-sm text-slate-500">
        <Link to="/" className="hover:text-brand-600">
          Home
        </Link>
        <span className="mx-2">/</span>
        <Link to="/products" className="hover:text-brand-600">
          Products
        </Link>
        {product.category_name && (
          <>
            <span className="mx-2">/</span>
            <span className="text-slate-900">{product.category_name}</span>
          </>
        )}
        <span className="mx-2">/</span>
        <span className="text-slate-900">{product.name}</span>
      </nav>

      <div className="grid gap-10 lg:grid-cols-2">
        {/* Gallery */}
        <div>
          <div className="overflow-hidden rounded-3xl border border-slate-200 bg-slate-100">
            <img
              src={images[imageIndex]?.url}
              alt={images[imageIndex]?.alt_text ?? product.name}
              onError={(event) => {
                event.currentTarget.src = IMAGE_FALLBACK;
              }}
              className="aspect-square w-full object-cover transition duration-300 hover:scale-[1.02]"
            />
          </div>
          {images.length > 1 && (
            <div className="mt-4 flex gap-3 overflow-x-auto pb-1">
              {images.map((image, index) => (
                <button
                  key={image.id ?? index}
                  type="button"
                  onClick={() => setImageIndex(index)}
                  aria-label={`View image ${index + 1}`}
                  className={`h-20 w-20 shrink-0 overflow-hidden rounded-xl border-2 transition ${
                    index === imageIndex
                      ? "border-brand-600"
                      : "border-slate-200 opacity-70 hover:opacity-100"
                  }`}
                >
                  <img
                    src={image.url}
                    alt=""
                    onError={(event) => {
                      event.currentTarget.src = IMAGE_FALLBACK;
                    }}
                    className="h-full w-full object-cover"
                  />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Info */}
        <div>
          <div className="flex items-center gap-3 text-xs">
            {product.brand_name && (
              <span className="font-bold uppercase tracking-wide text-brand-600">
                {product.brand_name}
              </span>
            )}
            <span className="text-slate-400">SKU: {product.sku}</span>
          </div>

          <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-900">
            {product.name}
          </h1>

          <div className="mt-3 flex flex-wrap items-center gap-3">
            <RatingStars value={product.rating} count={product.rating_count} size="text-base" showLabel />
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                inStock ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
              }`}
            >
              {inStock ? `In stock (${currentStock})` : "Out of stock"}
            </span>
          </div>

          <div className="mt-5">
            <Price price={product.price} salePrice={product.sale_price} size="lg" />
            {selectedVariant && selectedVariant.price && (
              <p className="mt-1 text-xs text-slate-500">
                Variant price for {selectedVariant.name}
              </p>
            )}
          </div>

          <p className="mt-4 leading-relaxed text-slate-600">{product.description}</p>

          {/* Variants */}
          {product.variants.length > 0 && (
            <fieldset className="mt-6">
              <legend className="text-sm font-bold uppercase tracking-wide text-slate-900">
                Options
              </legend>
              <div className="mt-3 flex flex-wrap gap-2">
                {product.variants.map((variant) => {
                  const selected = variant.id === selectedVariantId;
                  const disabled = variant.stock === 0;
                  return (
                    <button
                      key={variant.id}
                      type="button"
                      disabled={disabled}
                      onClick={() => {
                        setSelectedVariantId(variant.id);
                        setQuantity(1);
                      }}
                      className={`rounded-xl border px-4 py-2 text-sm font-semibold transition ${
                        selected
                          ? "border-brand-600 bg-brand-50 text-brand-700"
                          : "border-slate-300 bg-white text-slate-600 hover:border-brand-400"
                      } ${disabled ? "cursor-not-allowed opacity-40" : ""}`}
                      title={disabled ? "Out of stock" : undefined}
                    >
                      {variant.name ?? variant.sku}
                      {variant.price != null && (
                        <span className="ml-1 text-xs font-normal">({formatCurrency(variant.price)})</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </fieldset>
          )}

          {/* Quantity + actions */}
          <div className="mt-7 flex flex-wrap items-center gap-4">
            <QuantitySelector value={quantity} onChange={setQuantity} max={Math.max(currentStock, 1)} />
            <button
              type="button"
              onClick={handleAddToCart}
              disabled={!inStock}
              className="flex-1 rounded-xl bg-brand-600 px-6 py-3 font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              Add to cart
            </button>
            <button
              type="button"
              onClick={handleBuyNow}
              disabled={!inStock}
              className="flex-1 rounded-xl bg-slate-900 px-6 py-3 font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              Buy now
            </button>
            <button
              type="button"
              onClick={handleWishlist}
              aria-pressed={wishlisted}
              aria-label={wishlisted ? "Remove from wishlist" : "Add to wishlist"}
              className={`grid h-12 w-12 place-items-center rounded-xl border text-xl transition ${
                wishlisted
                  ? "border-red-200 bg-red-50 text-red-500"
                  : "border-slate-300 bg-white text-slate-400 hover:border-red-300 hover:text-red-500"
              }`}
            >
              {wishlisted ? "♥" : "♡"}
            </button>
          </div>

          {/* Meta */}
          <dl className="mt-6 grid grid-cols-2 gap-3 rounded-2xl bg-slate-50 p-4 text-sm">
            <div>
              <dt className="text-slate-500">Category</dt>
              <dd className="font-semibold text-slate-900">{product.category_name ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Added</dt>
              <dd className="font-semibold text-slate-900">{formatDate(product.created_at)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Ships</dt>
              <dd className="font-semibold text-slate-900">Free over $75</dd>
            </div>
            <div>
              <dt className="text-slate-500">Returns</dt>
              <dd className="font-semibold text-slate-900">30 days</dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Reviews */}
      <ReviewSection productId={product.id} />

      {/* Related */}
      <section className="mt-14">
        <h2 className="mb-6 text-xl font-extrabold text-slate-900">Related products</h2>
        {!relatedLoaded ? (
          <LoadingSpinner label="Loading related products…" size="sm" />
        ) : related.length === 0 ? (
          <p className="text-sm text-slate-500">No related products found.</p>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-4">
            {related.map((item) => (
              <ProductCard key={item.id} product={item} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
