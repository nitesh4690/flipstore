import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import useDocumentTitle from "../hooks/useDocumentTitle.js";

const schema = z
  .object({
    first_name: z.string().min(1, "First name is required"),
    last_name: z.string().min(1, "Last name is required"),
    email: z.string().email("Enter a valid email address"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirm_password: z.string(),
  })
  .refine((values) => values.password === values.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

export default function Register() {
  useDocumentTitle("Create account");
  const { register: registerUser } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [submitting, setSubmitting] = useState(false);

  const nextPath = new URLSearchParams(location.search).get("next") || "/";

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { first_name: "", last_name: "", email: "", password: "", confirm_password: "" },
  });

  const onSubmit = async (values) => {
    setSubmitting(true);
    try {
      const user = await registerUser({
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        password: values.password,
      });
      toast.success(`Account created — welcome, ${user.first_name}!`);
      navigate(nextPath, { replace: true });
    } catch (error) {
      toast.error(error.message || "Registration failed");
    } finally {
      setSubmitting(false);
    }
  };

  const fieldClass = (hasError) =>
    `h-11 w-full rounded-xl border px-3 text-sm outline-none transition ${
      hasError ? "border-red-400 focus:border-red-500" : "border-slate-300 focus:border-brand-500"
    }`;

  const fields = [
    ["first_name", "First name", "given-name", "text"],
    ["last_name", "Last name", "family-name", "text"],
    ["email", "Email address", "email", "email"],
    ["password", "Password", "new-password", "password"],
    ["confirm_password", "Confirm password", "new-password", "password"],
  ];

  return (
    <div className="mx-auto grid min-h-[70vh] max-w-md place-items-center px-4 py-12">
      <div className="w-full rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-extrabold text-slate-900">Create your account</h1>
        <p className="mt-1 text-sm text-slate-500">
          Join FlipStore for faster checkout, order tracking and wishlists.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4">
          {fields.map(([name, label, autoComplete, type]) => (
            <div key={name}>
              <label htmlFor={name} className="mb-1.5 block text-sm font-semibold text-slate-700">
                {label}
              </label>
              <input
                id={name}
                type={type}
                autoComplete={autoComplete}
                aria-invalid={Boolean(errors[name])}
                className={fieldClass(errors[name])}
                {...register(name)}
              />
              {errors[name] && (
                <p role="alert" className="mt-1 text-xs text-red-600">
                  {errors[name].message}
                </p>
              )}
            </div>
          ))}

          <button
            type="submit"
            disabled={submitting}
            className="h-11 w-full rounded-xl bg-brand-600 font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
          >
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          Already have an account?{" "}
          <Link
            to={`/login${location.search}`}
            className="font-semibold text-brand-600 hover:text-brand-700"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
