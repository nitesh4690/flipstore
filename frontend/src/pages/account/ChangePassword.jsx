import { useForm } from "react-hook-form";

import { useToast } from "../../context/ToastContext.jsx";
import useDocumentTitle from "../../hooks/useDocumentTitle.js";
import { changePassword } from "../../services/shop.js";

const label = "mb-1.5 block text-sm font-semibold text-slate-700";
const input =
  "h-11 w-full rounded-xl border border-slate-300 px-3 text-sm outline-none transition focus:border-brand-500";

/** Change account password. */
export default function ChangePassword() {
  useDocumentTitle("Change password");
  const toast = useToast();
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm();

  const onSubmit = async (values) => {
    try {
      await changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
      });
      toast.success("Password updated");
      reset();
    } catch (error) {
      toast.error(error.message || "Could not change password");
    }
  };

  return (
    <section className="max-w-lg rounded-2xl border border-slate-200 bg-white p-6">
      <h2 className="text-lg font-bold text-slate-900">Change password</h2>
      <p className="mt-1 text-sm text-slate-500">
        Use at least 8 characters, mixing letters and numbers.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-5 space-y-4">
        <div>
          <label htmlFor="cp-current" className={label}>Current password</label>
          <input
            id="cp-current"
            type="password"
            autoComplete="current-password"
            className={input}
            {...register("current_password", {
              required: "Enter your current password",
            })}
          />
          {errors.current_password && (
            <p className="mt-1 text-xs text-red-600">{errors.current_password.message}</p>
          )}
        </div>
        <div>
          <label htmlFor="cp-new" className={label}>New password</label>
          <input
            id="cp-new"
            type="password"
            autoComplete="new-password"
            className={input}
            {...register("new_password", {
              required: "Enter a new password",
              minLength: { value: 8, message: "At least 8 characters" },
            })}
          />
          {errors.new_password && (
            <p className="mt-1 text-xs text-red-600">{errors.new_password.message}</p>
          )}
        </div>
        <div>
          <label htmlFor="cp-confirm" className={label}>Confirm new password</label>
          <input
            id="cp-confirm"
            type="password"
            autoComplete="new-password"
            className={input}
            {...register("confirm", {
              required: "Repeat the new password",
              validate: (value) =>
                value === watch("new_password") || "Passwords do not match",
            })}
          />
          {errors.confirm && (
            <p className="mt-1 text-xs text-red-600">{errors.confirm.message}</p>
          )}
        </div>
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-xl bg-brand-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
        >
          {isSubmitting ? "Updating…" : "Update password"}
        </button>
      </form>
    </section>
  );
}
