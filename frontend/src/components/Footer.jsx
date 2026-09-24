import { useState } from "react";
import { Link } from "react-router-dom";

import { useToast } from "../context/ToastContext.jsx";

/** Site footer: brand blurb, links, service info and mini newsletter. */
export default function Footer() {
  const toast = useToast();
  const [email, setEmail] = useState("");

  const subscribe = (event) => {
    event.preventDefault();
    if (!/^\S+@\S+\.\S+$/.test(email)) {
      toast.error("Please enter a valid email address");
      return;
    }
    toast.success("Thanks for subscribing!");
    setEmail("");
  };

  const columns = [
    {
      title: "Shop",
      links: [
        ["All products", "/products"],
        ["New arrivals", "/products?sort=newest"],
        ["Best sellers", "/products?sort=popular"],
        ["Deals", "/products?sort=price_asc"],
      ],
    },
    {
      title: "Account",
      links: [
        ["Login", "/login"],
        ["Register", "/register"],
        ["Cart", "/cart"],
        ["Checkout", "/checkout"],
      ],
    },
    {
      title: "Customer service",
      links: [
        ["Shipping policy", "#"],
        ["Returns & refunds", "#"],
        ["FAQ", "#"],
        ["Contact us", "#"],
      ],
    },
  ];

  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-2 lg:grid-cols-5 lg:px-8">
        <div className="lg:col-span-2">
          <Link to="/" className="flex items-center gap-2 text-lg font-extrabold">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-brand-600 to-violet-600 text-white">
              F
            </span>
            FlipStore
          </Link>
          <p className="mt-3 max-w-sm text-sm text-slate-500">
            A modern full-stack e-commerce experience — fast, secure and built with
            React and FastAPI.
          </p>
          <form onSubmit={subscribe} className="mt-5 flex max-w-sm">
            <label htmlFor="footer-newsletter" className="sr-only">
              Email address
            </label>
            <input
              id="footer-newsletter"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="Your email address"
              className="h-10 w-full rounded-l-xl border border-slate-300 px-3 text-sm outline-none focus:border-brand-500"
            />
            <button
              type="submit"
              className="h-10 shrink-0 rounded-r-xl bg-brand-600 px-4 text-sm font-semibold text-white transition hover:bg-brand-700"
            >
              Subscribe
            </button>
          </form>
        </div>

        {columns.map((column) => (
          <nav key={column.title} aria-label={column.title}>
            <h3 className="text-sm font-bold uppercase tracking-wide text-slate-900">
              {column.title}
            </h3>
            <ul className="mt-4 space-y-2.5">
              {column.links.map(([label, href]) => (
                <li key={label}>
                  <Link
                    to={href}
                    className="text-sm text-slate-500 transition hover:text-brand-600"
                  >
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>

      <div className="border-t border-slate-100">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 py-5 text-xs text-slate-400 sm:flex-row sm:px-6 lg:px-8">
          <p>© {new Date().getFullYear()} FlipStore. All rights reserved.</p>
          <p>Secure payments · Free shipping over $75 · 30-day returns</p>
        </div>
      </div>
    </footer>
  );
}
