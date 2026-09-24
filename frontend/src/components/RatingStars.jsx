import { ratingLabel } from "../utils/format.js";

/**
 * Star rating rendered with a clipped overlay for partial fills.
 * `value` is 0–5; `count` is the number of reviews.
 */
export default function RatingStars({ value = 0, count, size = "text-base", showLabel = false }) {
  const rating = Math.max(0, Math.min(5, Number(value) || 0));
  const percent = (rating / 5) * 100;

  const stars = (color) => (
    <span className="flex" aria-hidden>
      {Array.from({ length: 5 }).map((_, index) => (
        <span key={index} className={color}>
          ★
        </span>
      ))}
    </span>
  );

  return (
    <div className="flex items-center gap-1.5" title={`${rating.toFixed(1)} out of 5`}>
      <span className={`relative inline-block leading-none ${size}`}>
        {stars("text-slate-300")}
        <span
          className="absolute inset-0 overflow-hidden leading-none"
          style={{ width: `${percent}%` }}
        >
          {stars("text-amber-400")}
        </span>
      </span>
      <span className="sr-only">{`${rating.toFixed(1)} out of 5 stars`}</span>
      <span className="text-xs font-medium text-slate-600">{rating.toFixed(1)}</span>
      {count !== undefined && <span className="text-xs text-slate-400">({count})</span>}
      {showLabel && <span className="text-xs text-slate-500">· {ratingLabel(rating)}</span>}
    </div>
  );
}
