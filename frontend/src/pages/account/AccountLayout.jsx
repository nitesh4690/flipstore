import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../../context/AuthContext.jsx";
import { useToast } from "../../context/ToastContext.jsx";

const NAV_ITEMS = [
  { to: "/account", label: "Profile", icon: "👤", end: true },
  { to: "/account/addresses", label: "Addresses", icon: "📍" },
  { to: "/account/orders", label: "Orders", icon: "📦" },
  { to: "/account/wishlist", label: "Wishlist", icon: "❤️" },
  { to: "/account/change-password", label: "Password", icon: "🔑" },
];

/** Sidebar layout for every /account page. */
export default function AccountLayout() {
  const { user, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();

  const handleLogout = async () => {
    // Server cart intentionally persists so it comes back on next sign-in;
    // CartContext switches back to the (empty) guest cart on its own.
    await logout();
    toast.info("Signed out");
    navigate("/");
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h1 className="text-2xl font-extrabold text-slate-900">My account</h1>
        <p className="mt-1 text-sm text-slate-500">
          Signed in as <strong>{user?.email}</strong>
        </p>
      </div>

      <div className="grid gap-8 md:grid-cols-[220px_1fr]">
        <nav className="flex gap-2 overflow-x-auto md:flex-col md:overflow-visible">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition ${
                  isActive
                    ? "bg-brand-600 text-white"
                    : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
                }`
              }
            >
              <span aria-hidden>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
          <button
            type="button"
            onClick={handleLogout}
            className="flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-red-500 ring-1 ring-red-100 transition hover:bg-red-50 md:mt-4"
          >
            <span aria-hidden>↩︎</span>
            Sign out
          </button>
        </nav>

        <div className="min-w-0">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
