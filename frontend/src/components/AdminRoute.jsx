import { Navigate, useLocation } from "react-router-dom";

import LoadingSpinner from "./LoadingSpinner.jsx";
import { useAuth } from "../context/AuthContext.jsx";

/**
 * Route guard for /admin/*: waits for session hydration, redirects guests to
 * /login?next=… and sends non-admin users back to the storefront.
 */
export default function AdminRoute({ children }) {
  const { isAuthenticated, initializing, user } = useAuth();
  const location = useLocation();

  if (initializing) return <LoadingSpinner label="Checking your session…" />;
  if (!isAuthenticated) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  if (user?.role !== "admin") {
    // Signed in but not an admin — never render admin UI.
    return <Navigate to="/" replace />;
  }
  return children;
}
