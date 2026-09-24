import { Navigate, useLocation } from "react-router-dom";

import LoadingSpinner from "./LoadingSpinner.jsx";
import { useAuth } from "../context/AuthContext.jsx";

/**
 * Route guard: waits for session hydration, then redirects guests to
 * /login?next=… so they land back on the page they wanted.
 */
export default function ProtectedRoute({ children }) {
  const { isAuthenticated, initializing } = useAuth();
  const location = useLocation();

  if (initializing) return <LoadingSpinner label="Checking your session…" />;
  if (!isAuthenticated) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  return children;
}
