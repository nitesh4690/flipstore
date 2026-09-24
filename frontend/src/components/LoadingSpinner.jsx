/** Accessible loading spinner with optional label. */
export default function LoadingSpinner({ label = "Loading…", size = "md" }) {
  const sizes = { sm: "h-5 w-5", md: "h-8 w-8", lg: "h-12 w-12" };
  return (
    <div role="status" className="flex flex-col items-center justify-center gap-3 py-12">
      <span
        className={`${sizes[size]} animate-spin rounded-full border-[3px] border-slate-200 border-t-brand-600`}
        aria-hidden
      />
      <span className="text-sm text-slate-500">{label}</span>
    </div>
  );
}
