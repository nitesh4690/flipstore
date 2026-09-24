import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <section className="grid min-h-screen place-items-center bg-slate-50 px-4 text-center">
      <div>
        <p className="text-6xl font-extrabold text-brand-600">404</p>
        <h1 className="mt-4 text-2xl font-bold text-slate-900">
          Page not found
        </h1>
        <p className="mt-2 text-slate-600">
          The page you are looking for doesn&apos;t exist or was moved.
        </p>
        <Link
          to="/"
          className="mt-6 inline-block rounded-xl bg-brand-600 px-6 py-3 font-semibold text-white hover:bg-brand-700"
        >
          Back to home
        </Link>
      </div>
    </section>
  );
}
