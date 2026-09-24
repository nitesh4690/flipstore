import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";

const NAV_ITEMS = [
  { to: "/admin", label: "Dashboard", icon: "📊", end: true },
  { to: "/admin/products", label: "Products", icon: "📦" },
  { to: "/admin/categories", label: "Categories", icon: "🏷️" },
  { to: "/admin/coupons", label: "Coupons", icon: "🎟️" },
  { to: "/admin/orders", label: "Orders", icon: "🧾" },
  { to: "/admin/customers", label: "Customers", icon: "👥" },
];

/** Sidebar layout for every /admin page (role-checked by AdminRoute). */
export default function AdminLayout() {
  const { user, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    toast.info("Signed out");
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
          <NavLink to="/admin" className="flex shrink-0 items-center gap-2 text-lg font-extrabold">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-slate-900 to-slate-700 text-white">
              F
            </span>
            <span>
              FlipStore <span className="text-brand-600">Admin</span>
            </span>
          </NavLink>

          <div className="ml-auto flex items-center gap-2">
            <NavLink
              to="/"
              className="hidden rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-brand-600 sm:block"
            >
              ← View store
            </NavLink>
            <span className="hidden max-w-40 truncate text-sm text-slate-500 md:block">
              {user?.email}
            </span>
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[220px_1fr] lg:px-8">
        <nav aria-label="Admin navigation" className="flex gap-2 overflow-x-auto lg:flex-col lg:overflow-visible">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition ${
                  isActive
                    ? "bg-slate-900 text-white"
                    : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
                }`
              }
            >
              <span aria-hidden>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <main className="min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
