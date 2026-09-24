import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import EmptyState from "../components/EmptyState.jsx";
import ProductCard from "../components/ProductCard.jsx";
import { ProductGridSkeleton } from "../components/Skeleton.jsx";
import useDocumentTitle from "../hooks/useDocumentTitle.js";
import { useToast } from "../context/ToastContext.jsx";
import {
  fetchBestSellers,
  fetchCategories,
  fetchFeatured,
  fetchNewArrivals,
} from "../services/catalog.js";
import { IMAGE_FALLBACK } from "../utils/format.js";

function SectionHeading({ title, subtitle, actionLabel, actionTo }) {
  return (
    <div className="mb-6 flex items-end justify-between gap-4">
      <div>
        <h2 className="text-2xl font-extrabold tracking-tight text-slate-900">{title}</h2>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actionLabel && (
        <Link
          to={actionTo}
          className="shrink-0 text-sm font-semibold text-brand-600 transition hover:text-brand-700"
        >
          {actionLabel} →
        </Link>
      )}
    </div>
  );
}

function ProductRow({ title, subtitle, loader, actionTo }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    loader(8)
      .then((data) => !cancelled && setProducts(data))
      .catch(() => !cancelled && setProducts([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [loader]);

  return (
    <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <SectionHeading title={title} subtitle={subtitle} actionLabel="View all" actionTo={actionTo} />
      {loading ? (
        <ProductGridSkeleton count={4} />
      ) : products.length === 0 ? (
        <EmptyState icon="📦" title="Nothing to show yet" description="Products will appear here once seeded." />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-4">
          {products.slice(0, 4).map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </section>
  );
}

export default function Home() {
  useDocumentTitle("");
  const toast = useToast();
  const [categories, setCategories] = useState([]);
  const [newsletterEmail, setNewsletterEmail] = useState("");

  useEffect(() => {
    fetchCategories()
      .then((data) => setCategories(data.filter((category) => category.parent_id === null).slice(0, 8)))
      .catch(() => setCategories([]));
  }, []);

  const subscribe = (event) => {
    event.preventDefault();
    if (!/^\S+@\S+\.\S+$/.test(newsletterEmail)) {
      toast.error("Please enter a valid email address");
      return;
    }
    toast.success("You're subscribed! Watch your inbox for deals.");
    setNewsletterEmail("");
  };

  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-brand-700 via-brand-600 to-violet-600">
        <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:px-8 lg:py-24">
          <div className="text-white">
            <span className="inline-block rounded-full bg-white/15 px-4 py-1.5 text-sm font-semibold backdrop-blur">
              New season · Up to 40% off
            </span>
            <h1 className="mt-5 text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl">
              Everything you love,
              <br />
              delivered fast.
            </h1>
            <p className="mt-4 max-w-lg text-lg text-brand-100">
              Shop electronics, fashion, home essentials and more — thousands of
              products, unbeatable prices, hassle-free returns.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to="/products"
                className="rounded-xl bg-white px-6 py-3 font-semibold text-brand-700 shadow-lg transition hover:bg-brand-50"
              >
                Shop now
              </Link>
              <Link
                to="/products?sort=newest"
                className="rounded-xl border border-white/40 px-6 py-3 font-semibold text-white transition hover:bg-white/10"
              >
                New arrivals
              </Link>
            </div>
          </div>

          <div className="relative hidden lg:block">
            <div className="grid grid-cols-2 gap-4">
              {["hero-1", "hero-2", "hero-3", "hero-4"].map((seed, index) => (
                <div
                  key={seed}
                  className={`overflow-hidden rounded-3xl shadow-2xl ${
                    index % 2 ? "translate-y-6" : ""
                  }`}
                >
                  <img
                    src={`https://picsum.photos/seed/${seed}/500/500`}
                    alt=""
                    onError={(event) => {
                      event.currentTarget.src = IMAGE_FALLBACK;
                    }}
                    className="h-56 w-full object-cover"
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Trust bar */}
      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto grid max-w-7xl grid-cols-2 gap-4 px-4 py-6 sm:px-6 lg:grid-cols-4 lg:px-8">
          {[
            ["🚚", "Free shipping", "On orders over $75"],
            ["↩️", "30-day returns", "No questions asked"],
            ["🔒", "Secure checkout", "Encrypted payments"],
            ["💬", "24/7 support", "We're here to help"],
          ].map(([icon, title, subtitle]) => (
            <div key={title} className="flex items-center gap-3">
              <span className="text-2xl" aria-hidden>
                {icon}
              </span>
              <div>
                <p className="text-sm font-bold text-slate-900">{title}</p>
                <p className="text-xs text-slate-500">{subtitle}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Categories */}
      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <SectionHeading
          title="Shop by category"
          subtitle="Find exactly what you're looking for"
          actionLabel="All categories"
          actionTo="/products"
        />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {categories.map((category) => (
            <Link
              key={category.id}
              to={`/products?category=${category.slug}`}
              className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-slate-100 shadow-sm transition hover:-translate-y-1 hover:shadow-md"
            >
              <div className="aspect-[4/3] overflow-hidden">
                <img
                  src={category.image_url || `https://picsum.photos/seed/${category.slug}/600/450`}
                  alt={category.name}
                  loading="lazy"
                  onError={(event) => {
                    event.currentTarget.src = IMAGE_FALLBACK;
                  }}
                  className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
                />
              </div>
              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-900/80 to-transparent p-4">
                <p className="font-bold text-white">{category.name}</p>
                <p className="text-xs text-slate-300">{category.product_count} products</p>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Featured */}
      <div className="bg-slate-50">
        <ProductRow
          title="Featured products"
          subtitle="Hand-picked highlights from our team"
          loader={fetchFeatured}
          actionTo="/products?is_featured=true"
        />
      </div>

      {/* Promos */}
      <section className="mx-auto grid max-w-7xl gap-6 px-4 py-12 sm:px-6 lg:grid-cols-2 lg:px-8">
        <div className="rounded-3xl bg-amber-50 p-8 sm:p-10">
          <p className="text-sm font-bold uppercase tracking-wide text-amber-600">Weekend deal</p>
          <h3 className="mt-2 text-2xl font-extrabold text-slate-900">
            Up to 30% off home & kitchen
          </h3>
          <p className="mt-2 text-sm text-slate-600">
            Upgrade your space with appliances and essentials at their lowest prices this season.
          </p>
          <Link
            to="/products?category=home-kitchen&sort=price_asc"
            className="mt-5 inline-block rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700"
          >
            Shop the deal
          </Link>
        </div>
        <div className="rounded-3xl bg-violet-50 p-8 sm:p-10">
          <p className="text-sm font-bold uppercase tracking-wide text-violet-600">New arrivals</p>
          <h3 className="mt-2 text-2xl font-extrabold text-slate-900">
            Fresh tech, just landed
          </h3>
          <p className="mt-2 text-sm text-slate-600">
            Be the first to grab the latest gadgets, wearables and audio gear.
          </p>
          <Link
            to="/products?sort=newest"
            className="mt-5 inline-block rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700"
          >
            Explore now
          </Link>
        </div>
      </section>

      {/* New arrivals */}
      <div className="border-y border-slate-200 bg-white">
        <ProductRow
          title="New arrivals"
          subtitle="The latest additions to the catalog"
          loader={fetchNewArrivals}
          actionTo="/products?sort=newest"
        />
      </div>

      {/* Best sellers */}
      <ProductRow
        title="Best sellers"
        subtitle="Customer favourites, restocked weekly"
        loader={fetchBestSellers}
        actionTo="/products?sort=popular"
      />

      {/* Newsletter */}
      <section className="bg-slate-900">
        <div className="mx-auto max-w-3xl px-4 py-14 text-center sm:px-6">
          <h2 className="text-3xl font-extrabold text-white">Get $10 off your first order</h2>
          <p className="mt-2 text-sm text-slate-400">
            Subscribe to our newsletter for exclusive deals, new drops and buying guides.
          </p>
          <form onSubmit={subscribe} className="mx-auto mt-6 flex max-w-md gap-2">
            <label htmlFor="newsletter-email" className="sr-only">
              Email address
            </label>
            <input
              id="newsletter-email"
              type="email"
              value={newsletterEmail}
              onChange={(event) => setNewsletterEmail(event.target.value)}
              placeholder="you@example.com"
              className="h-12 w-full rounded-xl border border-slate-700 bg-slate-800 px-4 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-brand-500"
            />
            <button
              type="submit"
              className="h-12 shrink-0 rounded-xl bg-brand-600 px-5 text-sm font-bold text-white transition hover:bg-brand-500"
            >
              Subscribe
            </button>
          </form>
        </div>
      </section>
    </>
  );
}
