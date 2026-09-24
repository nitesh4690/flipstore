import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";
import { useCart } from "../context/CartContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { fetchCategories } from "../services/catalog.js";
import SearchBar from "./SearchBar.jsx";

/**
 * Site header: logo, search, categories menu, auth links, cart badge.
 * Responsive: hamburger panel on mobile, hover dropdown-free nav on desktop.
 */
export default function Header() {
  const { isAuthenticated, user, logout } = useAuth();
  const { count } = useCart();
  const toast = useToast();
  const [categories, setCategories] = useState([]);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    fetchCategories()
      .then((data) => setCategories(data.filter((category) => category.parent_id === null)))
      .catch(() => setCategories([]));
  }, []);

  const handleLogout = async () => {
    await logout();
    toast.success("Signed out successfully");
    setMenuOpen(false);
  };

  const navLinkClass = ({ isActive }) =>
    `text-sm font-medium transition ${
      isActive ? "text-brand-600" : "text-slate-600 hover:text-brand-600"
    }`;

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
      {/* Main row */}
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex shrink-0 items-center gap-2 text-lg font-extrabold">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-brand-600 to-violet-600 text-white">
            F
          </span>
          <span className="hidden sm:inline">FlipStore</span>
        </Link>

        <div className="hidden flex-1 md:flex">
          <SearchBar />
        </div>

        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          {isAuthenticated ? (
            <div className="hidden items-center gap-2 sm:flex">
              {user?.role === "admin" && (
                <Link
                  to="/admin"
                  className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
                >
                  Admin
                </Link>
              )}
              <Link
                to="/account"
                className="max-w-36 truncate rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-brand-600"
              >
                Hi, {user?.first_name}
              </Link>
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-100"
              >
                Logout
              </button>
            </div>
          ) : (
            <div className="hidden items-center gap-1 sm:flex">
              <Link
                to="/login"
                className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-100"
              >
                Login
              </Link>
              <Link
                to="/register"
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
              >
                Register
              </Link>
            </div>
          )}

          <Link
            to="/cart"
            aria-label={`Shopping cart with ${count} items`}
            className="relative grid h-10 w-10 place-items-center rounded-xl bg-brand-600 text-white transition hover:bg-brand-700"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 0 0-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 0 0-16.536-1.84M7.5 14.25 5.106 5.272M6 20.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm12.75 0a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z" />
            </svg>
            {count > 0 && (
              <span className="absolute -right-1.5 -top-1.5 grid h-5 min-w-5 place-items-center rounded-full bg-red-500 px-1 text-[11px] font-bold text-white">
                {count > 99 ? "99+" : count}
              </span>
            )}
          </Link>

          {/* Mobile hamburger */}
          <button
            type="button"
            aria-label="Toggle menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
            className="grid h-10 w-10 place-items-center rounded-xl border border-slate-200 text-slate-600 transition hover:bg-slate-50 md:hidden"
          >
            {menuOpen ? "✕" : "☰"}
          </button>
        </div>
      </div>

      {/* Categories bar (desktop) */}
      <nav
        aria-label="Categories"
        className="hidden border-t border-slate-100 md:block"
      >
        <div className="mx-auto flex max-w-7xl items-center gap-6 overflow-x-auto px-6 py-2.5 lg:px-8">
          <NavLink to="/products" className={navLinkClass}>
            All Products
          </NavLink>
          {categories.slice(0, 8).map((category) => (
            <NavLink
              key={category.id}
              to={`/products?category=${category.slug}`}
              className={({ isActive }) =>
                `whitespace-nowrap text-sm font-medium transition ${
                  isActive ? "text-brand-600" : "text-slate-600 hover:text-brand-600"
                }`
              }
            >
              {category.name}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Mobile panel */}
      {menuOpen && (
        <div className="border-t border-slate-100 bg-white px-4 pb-4 pt-3 md:hidden">
          <SearchBar fullWidth />
          <nav aria-label="Mobile navigation" className="mt-3 flex flex-col gap-1">
            <NavLink
              to="/products"
              onClick={() => setMenuOpen(false)}
              className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              All Products
            </NavLink>
            {categories.map((category) => (
              <NavLink
                key={category.id}
                to={`/products?category=${category.slug}`}
                onClick={() => setMenuOpen(false)}
                className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                {category.name}
              </NavLink>
            ))}
            <div className="mt-2 border-t border-slate-100 pt-2">
              {isAuthenticated ? (
                <div className="flex items-center justify-between px-3 py-2">
                  <Link
                    to="/account"
                    onClick={() => setMenuOpen(false)}
                    className="text-sm font-medium text-slate-700"
                  >
                    Hi, {user?.first_name} · My account
                  </Link>
                  <div className="flex items-center gap-3">
                    {user?.role === "admin" && (
                      <Link
                        to="/admin"
                        onClick={() => setMenuOpen(false)}
                        className="text-sm font-semibold text-slate-900"
                      >
                        Admin
                      </Link>
                    )}
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="text-sm font-semibold text-brand-600"
                    >
                      Logout
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex gap-2 px-3 py-2">
                  <Link
                    to="/login"
                    onClick={() => setMenuOpen(false)}
                    className="flex-1 rounded-xl border border-slate-300 px-4 py-2 text-center text-sm font-semibold text-slate-700"
                  >
                    Login
                  </Link>
                  <Link
                    to="/register"
                    onClick={() => setMenuOpen(false)}
                    className="flex-1 rounded-xl bg-brand-600 px-4 py-2 text-center text-sm font-semibold text-white"
                  >
                    Register
                  </Link>
                </div>
              )}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
