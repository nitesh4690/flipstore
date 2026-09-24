import { useEffect } from "react";
import { useForm } from "react-hook-form";

import LoadingSpinner from "../../components/LoadingSpinner.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { useToast } from "../../context/ToastContext.jsx";
import useDocumentTitle from "../../hooks/useDocumentTitle.js";
import { updateProfile } from "../../services/shop.js";

const label = "mb-1.5 block text-sm font-semibold text-slate-700";
const input =
  "h-11 w-full rounded-xl border border-slate-300 px-3 text-sm outline-none transition focus:border-brand-500";

/** Profile view + edit (name / phone). */
export default function Profile() {
  useDocumentTitle("My profile");
  const { user, setUser } = useAuth();
  const toast = useToast();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm();

  useEffect(() => {
    if (user) {
      reset({
        first_name: user.first_name,
        last_name: user.last_name,
        phone: user.phone ?? "",
      });
    }
  }, [user, reset]);

  if (!user) return <LoadingSpinner label="Loading profile…" />;

  const onSubmit = async (values) => {
    try {
      const updated = await updateProfile({
        first_name: values.first_name.trim(),
        last_name: values.last_name.trim(),
        phone: values.phone.trim() || null,
      });
      setUser(updated);
      toast.success("Profile updated");
    } catch (error) {
      toast.error(error.message || "Could not update profile");
    }
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6">
      <h2 className="text-lg font-bold text-slate-900">Profile details</h2>
      <p className="mt-1 text-sm text-slate-500">
        Your email is your sign-in and can't be changed here.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-5 grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="pf-first" className={label}>First name</label>
          <input
            id="pf-first"
            className={input}
            {...register("first_name", { required: "First name is required" })}
          />
          {errors.first_name && (
            <p className="mt-1 text-xs text-red-600">{errors.first_name.message}</p>
          )}
        </div>
        <div>
          <label htmlFor="pf-last" className={label}>Last name</label>
          <input
            id="pf-last"
            className={input}
            {...register("last_name", { required: "Last name is required" })}
          />
          {errors.last_name && (
            <p className="mt-1 text-xs text-red-600">{errors.last_name.message}</p>
          )}
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="pf-email" className={label}>Email</label>
          <input
            id="pf-email"
            className={`${input} bg-slate-50 text-slate-500`}
            value={user.email}
            readOnly
          />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="pf-phone" className={label}>Phone (optional)</label>
          <input
            id="pf-phone"
            type="tel"
            className={input}
            {...register("phone", { maxLength: { value: 30, message: "Too long" } })}
          />
          {errors.phone && (
            <p className="mt-1 text-xs text-red-600">{errors.phone.message}</p>
          )}
        </div>
        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded-xl bg-brand-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
          >
            {isSubmitting ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>
    </section>
  );
}
