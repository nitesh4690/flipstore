import { useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import {
  createReview,
  deleteReview,
  fetchReviews,
  updateReview,
} from "../services/catalog.js";
import { formatDate } from "../utils/format.js";
import ConfirmDialog from "./ConfirmDialog.jsx";
import EmptyState from "./EmptyState.jsx";
import LoadingSpinner from "./LoadingSpinner.jsx";
import Pagination from "./Pagination.jsx";
import RatingStars from "./RatingStars.jsx";

const SORTS = [
  { id: "newest", label: "Most recent" },
  { id: "highest", label: "Highest rated" },
  { id: "lowest", label: "Lowest rated" },
];

const field =
  "h-11 w-full rounded-xl border border-slate-300 px-3 text-sm outline-none transition focus:border-brand-500";

function Avatar({ firstName, lastName }) {
  const initials =
    `${firstName?.[0] ?? ""}${lastName?.[0] ?? ""}`.toUpperCase() || "?";
  return (
    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-100 text-xs font-extrabold text-brand-700">
      {initials}
    </span>
  );
}

function StarPicker({ value, onChange }) {
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          aria-label={`Rate ${star} star${star > 1 ? "s" : ""}`}
          className={`text-2xl leading-none transition hover:scale-110 ${
            star <= value ? "text-amber-400" : "text-slate-300"
          }`}
        >
          ★
        </button>
      ))}
      <span className="ml-2 text-sm font-semibold text-slate-600">{value}.0</span>
    </div>
  );
}

function DistributionBar({ star, count, total }) {
  const width = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-6 text-right font-semibold text-slate-500">{star}★</span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-amber-400" style={{ width: `${width}%` }} />
      </div>
      <span className="w-7 text-right tabular-nums text-slate-500">{count}</span>
    </div>
  );
}

/**
 * Full reviews block for a product: rating summary + distribution bars,
 * sort/pagination, and write/edit/delete for the signed-in customer's review.
 */
export default function ReviewSection({ productId }) {
  const { user, isAuthenticated } = useAuth();
  const toast = useToast();
  const location = useLocation();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("newest");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null); // my review being edited
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(() => {
    fetchReviews(productId, { page, limit: 5, sort })
      .then(setData)
      .catch((error) => {
        setData(null);
        toast.error(error.message || "Could not load reviews");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId, page, sort]);

  useEffect(() => {
    setPage(1);
    setFormOpen(false);
    setEditing(null);
    setData(null);
  }, [productId]);

  useEffect(() => {
    load();
  }, [load]);

  const myReview = data?.items.find((item) => item.is_mine) ?? null;
  const summary = data?.summary;
  const total = data?.total ?? 0;

  const openWrite = () => {
    if (!isAuthenticated) {
      navigate(`/login?next=${encodeURIComponent(location.pathname)}`);
      return;
    }
    if (myReview) {
      setEditing(myReview);
      setRating(myReview.rating);
      setComment(myReview.comment ?? "");
    } else {
      setEditing(null);
      setRating(5);
      setComment("");
    }
    setFormOpen(true);
  };

  const closeForm = () => {
    setFormOpen(false);
    setEditing(null);
    setRating(5);
    setComment("");
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      const payload = { rating, comment: comment.trim() || null };
      const response = editing
        ? await updateReview(editing.id, payload)
        : await createReview(productId, payload);
      toast.success(response.message || "Review saved");
      closeForm();
      setPage(1);
      load();
    } catch (error) {
      toast.error(error.message || "Could not save review");
    } finally {
      setBusy(false);
    }
  };

  const confirmDelete = async () => {
    if (!myReview) return;
    try {
      const response = await deleteReview(myReview.id);
      toast.success(response.message || "Review deleted");
      setDeleting(false);
      setPage(1);
      load();
    } catch (error) {
      toast.error(error.message || "Could not delete review");
      setDeleting(false);
    }
  };

  if (!data) return <LoadingSpinner label="Loading reviews…" size="sm" />;

  return (
    <section
      id="reviews"
      className="mt-14 rounded-3xl border border-slate-200 bg-white p-6 sm:p-8"
    >
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-xl font-extrabold text-slate-900">Customer reviews</h2>
        <button
          type="button"
          onClick={openWrite}
          className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          {myReview ? "Edit my review" : "Write a review"}
        </button>
      </div>

      {/* Summary */}
      <div className="mt-6 grid gap-8 sm:grid-cols-[220px_1fr]">
        <div className="rounded-2xl bg-slate-50 p-5 text-center">
          <p className="text-4xl font-extrabold text-slate-900">
            {Number(summary?.average ?? 0).toFixed(1)}
          </p>
          <div className="mt-2 flex justify-center">
            <RatingStars value={summary?.average ?? 0} size="text-lg" />
          </div>
          <p className="mt-1 text-sm text-slate-500">
            {total} review{total === 1 ? "" : "s"}
          </p>
        </div>

        <div className="space-y-2 self-center">
          {[5, 4, 3, 2, 1].map((star) => (
            <DistributionBar
              key={star}
              star={star}
              count={summary?.distribution?.[String(star)] ?? 0}
              total={summary?.count ?? 0}
            />
          ))}
        </div>
      </div>

      {/* Write / edit form */}
      {formOpen && (
        <form onSubmit={onSubmit} className="mt-6 space-y-4 rounded-2xl bg-slate-50 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-bold uppercase tracking-wide text-slate-900">
              {editing ? "Edit your review" : "Write your review"}
            </h3>
            <StarPicker value={rating} onChange={setRating} />
          </div>
          <div>
            <label htmlFor="review-comment" className="sr-only">
              Your review
            </label>
            <textarea
              id="review-comment"
              rows="4"
              maxLength="2000"
              placeholder="What did you like or dislike? (optional — you can also rate only)"
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-brand-500"
            />
          </div>
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={closeForm}
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={busy}
              className="rounded-xl bg-brand-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {busy ? "Saving…" : editing ? "Save changes" : "Publish review"}
            </button>
          </div>
        </form>
      )}

      {/* List */}
      <div className="mt-8 flex items-center justify-between gap-3">
        <p className="text-sm text-slate-500">
          Showing {data.items.length} of {total}
        </p>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          Sort by
          <select
            value={sort}
            onChange={(event) => {
              setSort(event.target.value);
              setPage(1);
            }}
            className="h-10 rounded-xl border border-slate-300 px-3 text-sm outline-none transition focus:border-brand-500"
          >
            {SORTS.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {data.items.length === 0 ? (
        <div className="mt-4">
          <EmptyState
            icon="⭐"
            title="No reviews yet"
            description="Be the first to share what you think about this product."
            actionLabel={isAuthenticated ? undefined : "Sign in to review"}
            onAction={isAuthenticated ? undefined : openWrite}
          />
        </div>
      ) : (
        <ul className="mt-4 space-y-4">
          {data.items.map((review) => (
            <li key={review.id} className="rounded-2xl border border-slate-100 p-4 sm:p-5">
              <div className="flex flex-wrap items-center gap-3">
                <Avatar firstName={review.user?.first_name} lastName={review.user?.last_name} />
                <div className="min-w-0">
                  <p className="flex flex-wrap items-center gap-2 text-sm font-bold text-slate-900">
                    {[review.user?.first_name, review.user?.last_name]
                      .filter(Boolean)
                      .join(" ") || "Customer"}
                    {review.is_mine && (
                      <span className="rounded bg-brand-100 px-1.5 py-0.5 text-[10px] font-extrabold uppercase text-brand-700">
                        You
                      </span>
                    )}
                    {review.verified && (
                      <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-extrabold uppercase text-emerald-700">
                        Verified purchase
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-slate-400">{formatDate(review.created_at)}</p>
                </div>
                <div className="ml-auto">
                  <RatingStars value={review.rating} />
                </div>
              </div>

              {review.comment && (
                <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-slate-600">
                  {review.comment}
                </p>
              )}

              {review.is_mine && (
                <div className="mt-3 flex gap-3 text-xs font-semibold">
                  <button
                    type="button"
                    onClick={openWrite}
                    className="text-brand-600 transition hover:text-brand-700"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeleting(true)}
                    className="text-red-500 transition hover:text-red-600"
                  >
                    Delete
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      <Pagination page={data.page} totalPages={data.total_pages} onPageChange={setPage} />

      {!isAuthenticated && (
        <p className="mt-6 border-t border-slate-100 pt-4 text-center text-sm text-slate-500">
          <button
            type="button"
            onClick={openWrite}
            className="font-semibold text-brand-600 transition hover:text-brand-700"
          >
            Sign in
          </button>{" "}
          to write a review.
        </p>
      )}

      <ConfirmDialog
        open={deleting}
        title="Delete your review?"
        message="Your review and rating will be permanently removed."
        confirmLabel="Delete"
        danger
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(false)}
      />
    </section>
  );
}
