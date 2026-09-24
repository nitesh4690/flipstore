import { Outlet } from "react-router-dom";

import Footer from "../components/Footer.jsx";
import Header from "../components/Header.jsx";

/** Base layout for all customer-facing pages (header / content / footer). */
export default function StoreLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
