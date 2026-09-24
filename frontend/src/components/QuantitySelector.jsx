/**
 * Quantity stepper with min/max bounds and keyboard support.
 */
export default function QuantitySelector({
  value,
  onChange,
  min = 1,
  max = 99,
  id = "quantity",
}) {
  const clamp = (next) => Math.max(min, Math.min(next, max));

  return (
    <div className="inline-flex items-center rounded-xl border border-slate-300 bg-white">
      <button
        type="button"
        aria-label="Decrease quantity"
        disabled={value <= min}
        onClick={() => onChange(clamp(value - 1))}
        className="grid h-10 w-10 place-items-center rounded-l-xl text-lg text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
      >
        −
      </button>
      <input
        id={id}
        type="number"
        inputMode="numeric"
        aria-label="Quantity"
        value={value}
        onChange={(event) => {
          const next = Number.parseInt(event.target.value, 10);
          onChange(Number.isNaN(next) ? min : clamp(next));
        }}
        className="h-10 w-14 border-x border-slate-300 bg-transparent text-center text-sm font-semibold outline-none [appearance:textfield] focus:ring-0 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
      />
      <button
        type="button"
        aria-label="Increase quantity"
        disabled={value >= max}
        onClick={() => onChange(clamp(value + 1))}
        className="grid h-10 w-10 place-items-center rounded-r-xl text-lg text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
      >
        +
      </button>
    </div>
  );
}
