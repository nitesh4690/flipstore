import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

/** Keyword search box — submits to /products?search=… */
export default function SearchBar({ fullWidth = false, autoFocus = false }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [term, setTerm] = useState(searchParams.get("search") ?? "");

  const submit = (event) => {
    event.preventDefault();
    const query = term.trim();
    navigate(query ? `/products?search=${encodeURIComponent(query)}` : "/products");
  };

  return (
    <form
      role="search"
      onSubmit={submit}
      className={`flex items-center ${fullWidth ? "w-full" : "w-full max-w-xl"}`}
    >
      <label htmlFor="site-search" className="sr-only">
        Search products
      </label>
      <div className="relative flex w-full">
        <input
          id="site-search"
          type="search"
          value={term}
          autoFocus={autoFocus}
          onChange={(event) => setTerm(event.target.value)}
          placeholder="Search products, brands and more…"
          className="h-10 w-full rounded-l-xl border border-r-0 border-slate-300 bg-slate-50 pl-4 pr-10 text-sm outline-none transition placeholder:text-slate-400 focus:border-brand-500 focus:bg-white"
        />
        <button
          type="submit"
          aria-label="Search"
          className="grid h-10 w-11 place-items-center rounded-r-xl border border-brand-600 bg-brand-600 text-white transition hover:bg-brand-700"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-4.35-4.35M17 10.5a6.5 6.5 0 1 1-13 0 6.5 6.5 0 0 1 13 0Z" />
          </svg>
        </button>
      </div>
    </form>
  );
}
