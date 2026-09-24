import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import EmptyState from "../components/EmptyState.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useCart } from "../context/CartContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import useDocumentTitle from "../hooks/useDocumentTitle.js";
import { getAddresses, placeOrder } from "../services/shop.js";
import { IMAGE_FALLBACK, formatCurrency, formatDate } from "../utils/format.js";

const STEPS = [
  "Information",
  "Shipping address",
  "Billing address",
  "Shipping method",
  "Payment",
  "Review",
  "Confirmation",
];

const SHIPPING_METHODS = [
  { id: "standard", name: "Standard", eta: "3–5 business days", price: 9.99 },
  { id: "express", name: "Express", eta: "1–2 business days", price: 19.99 },
  { id: "pickup", name: "Store pickup", eta: "Ready in 24 hours", price: 0 },
];

const round2 = (value) => Math.round((Number(value) + Number.EPSILON) * 100) / 100;

const BLANK_ADDRESS = {
  label: "Home",
  full_name: "",
  phone: "",
  line1: "",
  line2: "",
  city: "",
  state: "",
  postal_code: "",
  country: "United States",
};

function addressComplete(form) {
  return Boolean(form.full_name && form.line1 && form.city && form.postal_code && form.country);
}

const label = "mb-1.5 block text-sm font-semibold text-slate-700";
const input =
  "h-11 w-full rounded-xl border border-slate-300 px-3 text-sm outline-none transition focus:border-brand-500";

function AddressForm({ form, setForm, errors = {} }) {
  const field = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const rows = [
    ["label", "Label", "text"],
    ["full_name", "Full name", "text"],
    ["phone", "Phone (optional)", "tel"],
    ["line1", "Address line 1", "text"],
    ["line2", "Address line 2 (optional)", "text"],
    ["city", "City", "text"],
    ["state", "State / Province", "text"],
    ["postal_code", "Postal code", "text"],
    ["country", "Country", "text"],
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {rows.map(([key, name, type]) => (
        <div key={key} className={key === "line1" || key === "line2" ? "sm:col-span-2" : ""}>
          <label htmlFor={`addr-${key}`} className={label}>
            {name}
          </label>
          <input
            id={`addr-${key}`}
            type={type}
            value={form[key]}
            onChange={(event) => field(key, event.target.value)}
            className={`${input} ${errors[key] ? "border-red-400" : ""}`}
          />
          {errors[key] && <p className="mt-1 text-xs text-red-600">{errors[key]}</p>}
        </div>
      ))}
    </div>
  );
}

/** 7-step checkout: info → shipping → billing → method → payment → review → confirmation. */
export default function Checkout() {
  useDocumentTitle("Checkout");
  const { user } = useAuth();
  const { items, totals, couponCode, clearCart } = useCart();
  const toast = useToast();
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [addresses, setAddresses] = useState(null); // null = loading
  const [customer, setCustomer] = useState({
    first_name: user?.first_name ?? "",
    last_name: user?.last_name ?? "",
    phone: user?.phone ?? "",
  });

  const [shippingMode, setShippingMode] = useState("saved");
  const [shippingAddressId, setShippingAddressId] = useState(null);
  const [shippingForm, setShippingForm] = useState(BLANK_ADDRESS);

  const [billingSame, setBillingSame] = useState(true);
  const [billingMode, setBillingMode] = useState("saved");
  const [billingAddressId, setBillingAddressId] = useState(null);
  const [billingForm, setBillingForm] = useState(BLANK_ADDRESS);

  const [shippingMethod, setShippingMethod] = useState("standard");
  const [paymentMethod, setPaymentMethod] = useState("card_mock");
  const [card, setCard] = useState({ number: "", expiry: "", cvc: "" });
  const [notes, setNotes] = useState("");

  const [errors, setErrors] = useState({});
  const [placing, setPlacing] = useState(false);
  const [placedOrder, setPlacedOrder] = useState(null);

  useEffect(() => {
    getAddresses()
      .then((rows) => {
        setAddresses(rows);
        const defaultShipping = rows.find((row) => row.is_default_shipping) ?? rows[0];
        if (defaultShipping) setShippingAddressId(defaultShipping.id);
        const defaultBilling = rows.find((row) => row.is_default_billing) ?? rows[0];
        if (defaultBilling) setBillingAddressId(defaultBilling.id);
        if (rows.length === 0) setShippingMode("new");
      })
      .catch(() => {
        setAddresses([]);
        setShippingMode("new");
      });
  }, []);

  /* Totals for the chosen shipping method (server cart totals assume standard). */
  const reviewTotals = useMemo(() => {
    const base = round2(totals.subtotal - totals.discount);
    const method = SHIPPING_METHODS.find((entry) => entry.id === shippingMethod);
    const shipping =
      shippingMethod === "standard" ? (base >= 75 ? 0 : 9.99) : (method?.price ?? 0);
    const tax = round2(base * 0.08);
    return { base, shipping, tax, total: round2(base + shipping + tax) };
  }, [totals, shippingMethod]);

  if (items.length === 0 && !placedOrder) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <EmptyState
          icon="🛒"
          title="Nothing to check out"
          description="Your cart is empty — add some products first."
          actionLabel="Browse products"
          onAction={() => navigate("/products")}
        />
      </div>
    );
  }

  if (addresses === null) return <LoadingSpinner label="Loading your addresses…" />;

  /* ------------------------------------------------------------------ */
  /* Validation                                                          */
  /* ------------------------------------------------------------------ */
  const validate = (atStep) => {
    const next = {};
    if (atStep === 1) {
      if (!customer.first_name.trim()) next.first_name = "Required";
      if (!customer.last_name.trim()) next.last_name = "Required";
    }
    if (atStep === 2) {
      if (shippingMode === "saved" && !shippingAddressId) next.shipping = "Select an address";
      if (shippingMode === "new" && !addressComplete(shippingForm)) {
        if (!shippingForm.full_name) next.full_name = "Required";
        if (!shippingForm.line1) next.line1 = "Required";
        if (!shippingForm.city) next.city = "Required";
        if (!shippingForm.postal_code) next.postal_code = "Required";
      }
    }
    if (atStep === 3 && !billingSame) {
      if (billingMode === "saved" && !billingAddressId) next.billing = "Select an address";
      if (billingMode === "new" && !addressComplete(billingForm)) next.billing = "Complete the billing address";
    }
    if (atStep === 5 && paymentMethod === "card_mock") {
      const digits = card.number.replace(/\s+/g, "");
      if (!/^\d{16}$/.test(digits)) next.card_number = "Enter a 16-digit card number";
      if (!/^\d{2}\/\d{2}$/.test(card.expiry)) next.expiry = "MM/YY";
      if (!/^\d{3,4}$/.test(card.cvc)) next.cvc = "3–4 digits";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const continueTo = (nextStep) => {
    if (validate(step)) {
      setStep(nextStep);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  /* ------------------------------------------------------------------ */
  /* Placement                                                           */
  /* ------------------------------------------------------------------ */
  const buildPayload = () => {
    const payload = {
      shipping_method: shippingMethod,
      payment_method: paymentMethod,
      billing_same_as_shipping: billingSame,
      notes: notes.trim() || null,
      ...(shippingMode === "saved"
        ? { shipping_address_id: shippingAddressId }
        : { shipping_address: shippingForm }),
    };
    if (!billingSame) {
      Object.assign(
        payload,
        billingMode === "saved"
          ? { billing_address_id: billingAddressId }
          : { billing_address: billingForm },
      );
    }
    if (paymentMethod === "card_mock") {
      // Sent to the mock gateway: 4242… succeeds, 4000…0002 is declined
      payload.card = {
        number: card.number.trim(),
        expiry: card.expiry.trim(),
        cvc: card.cvc.trim(),
      };
    }
    return payload;
  };

  const placeOrderNow = async () => {
    setPlacing(true);
    try {
      const order = await placeOrder(buildPayload());
      setPlacedOrder(order);
      setStep(7);
      await clearCart(); // server already emptied it; refresh client state + badge
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      toast.error(error.message || "Could not place the order");
    } finally {
      setPlacing(false);
    }
  };

  /* ------------------------------------------------------------------ */
  /* Renderers                                                           */
  /* ------------------------------------------------------------------ */
  const addressCard = (address, selectedId, onSelect) => (
    <label
      key={address.id}
      className={`flex cursor-pointer gap-3 rounded-xl border p-4 transition ${
        selectedId === address.id
          ? "border-brand-600 bg-brand-50"
          : "border-slate-200 hover:border-brand-300"
      }`}
    >
      <input
        type="radio"
        name="picked-address"
        checked={selectedId === address.id}
        onChange={() => onSelect(address.id)}
        className="mt-1 accent-brand-600"
      />
      <span className="text-sm">
        <span className="font-semibold text-slate-900">{address.label}</span>{" "}
        {address.is_default_shipping && (
          <span className="ml-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-slate-500">
            default
          </span>
        )}
        <span className="mt-1 block text-slate-600">
          {address.full_name} · {address.line1}
          {address.line2 ? `, ${address.line2}` : ""}, {address.city}{" "}
          {address.postal_code}, {address.country}
        </span>
        {address.phone && <span className="block text-slate-500">{address.phone}</span>}
      </span>
    </label>
  );

  const modeToggle = (mode, setMode) => (
    <div className="mb-4 flex gap-2">
      {addresses.length > 0 && (
        <button
          type="button"
          onClick={() => setMode("saved")}
          className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
            mode === "saved" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600"
          }`}
        >
          Saved addresses
        </button>
      )}
      <button
        type="button"
        onClick={() => setMode("new")}
        className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
          mode === "new" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600"
        }`}
      >
        Use a new address
      </button>
    </div>
  );

  const stepContent = () => {
    switch (step) {
      case 1:
        return (
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="co-first" className={label}>First name</label>
              <input
                id="co-first"
                className={input}
                value={customer.first_name}
                onChange={(event) =>
                  setCustomer((c) => ({ ...c, first_name: event.target.value }))
                }
              />
              {errors.first_name && <p className="mt-1 text-xs text-red-600">{errors.first_name}</p>}
            </div>
            <div>
              <label htmlFor="co-last" className={label}>Last name</label>
              <input
                id="co-last"
                className={input}
                value={customer.last_name}
                onChange={(event) => setCustomer((c) => ({ ...c, last_name: event.target.value }))}
              />
              {errors.last_name && <p className="mt-1 text-xs text-red-600">{errors.last_name}</p>}
            </div>
            <div>
              <label htmlFor="co-email" className={label}>Email</label>
              <input id="co-email" className={`${input} bg-slate-50`} value={user?.email ?? ""} readOnly />
            </div>
            <div>
              <label htmlFor="co-phone" className={label}>Phone (optional)</label>
              <input
                id="co-phone"
                type="tel"
                className={input}
                value={customer.phone}
                onChange={(event) => setCustomer((c) => ({ ...c, phone: event.target.value }))}
              />
            </div>
          </div>
        );

      case 2:
        return (
          <div>
            {modeToggle(shippingMode, setShippingMode)}
            {shippingMode === "saved" ? (
              <div className="space-y-3">
                {addresses.map((address) =>
                  addressCard(address, shippingAddressId, setShippingAddressId),
                )}
                {errors.shipping && <p className="text-xs text-red-600">{errors.shipping}</p>}
              </div>
            ) : (
              <AddressForm form={shippingForm} setForm={setShippingForm} errors={errors} />
            )}
          </div>
        );

      case 3:
        return (
          <div>
            <label className="flex items-center gap-3 rounded-xl bg-slate-50 p-4 text-sm font-medium text-slate-700">
              <input
                type="checkbox"
                checked={billingSame}
                onChange={(event) => setBillingSame(event.target.checked)}
                className="h-4 w-4 accent-brand-600"
              />
              Billing address is the same as shipping
            </label>
            {!billingSame && (
              <div className="mt-4">
                {modeToggle(billingMode, setBillingMode)}
                {billingMode === "saved" ? (
                  <div className="space-y-3">
                    {addresses.map((address) =>
                      addressCard(address, billingAddressId, setBillingAddressId),
                    )}
                    {errors.billing && <p className="text-xs text-red-600">{errors.billing}</p>}
                  </div>
                ) : (
                  <AddressForm form={billingForm} setForm={setBillingForm} />
                )}
                {errors.billing && billingMode === "new" && (
                  <p className="mt-2 text-xs text-red-600">{errors.billing}</p>
                )}
              </div>
            )}
          </div>
        );

      case 4:
        return (
          <div className="space-y-3">
            {SHIPPING_METHODS.map((method) => {
              const price =
                method.id === "standard"
                  ? reviewTotals.base >= 75
                    ? "FREE"
                    : formatCurrency(method.price)
                  : method.price === 0
                    ? "FREE"
                    : formatCurrency(method.price);
              return (
                <label
                  key={method.id}
                  className={`flex cursor-pointer items-center gap-3 rounded-xl border p-4 transition ${
                    shippingMethod === method.id
                      ? "border-brand-600 bg-brand-50"
                      : "border-slate-200 hover:border-brand-300"
                  }`}
                >
                  <input
                    type="radio"
                    name="shipping-method"
                    checked={shippingMethod === method.id}
                    onChange={() => setShippingMethod(method.id)}
                    className="accent-brand-600"
                  />
                  <span className="flex-1 text-sm">
                    <span className="font-semibold text-slate-900">{method.name}</span>
                    <span className="block text-slate-500">{method.eta}</span>
                  </span>
                  <span className="font-bold text-slate-900">{price}</span>
                </label>
              );
            })}
          </div>
        );

      case 5:
        return (
          <div className="space-y-4">
            {[
              ["card_mock", "Credit / debit card", "Mock gateway — you won't be charged"],
              ["cod", "Cash on delivery", "Pay when your order arrives"],
            ].map(([id, name, hint]) => (
              <label
                key={id}
                className={`flex cursor-pointer gap-3 rounded-xl border p-4 transition ${
                  paymentMethod === id
                    ? "border-brand-600 bg-brand-50"
                    : "border-slate-200 hover:border-brand-300"
                }`}
              >
                <input
                  type="radio"
                  name="payment"
                  checked={paymentMethod === id}
                  onChange={() => setPaymentMethod(id)}
                  className="mt-1 accent-brand-600"
                />
                <span className="text-sm">
                  <span className="font-semibold text-slate-900">{name}</span>
                  <span className="block text-slate-500">{hint}</span>
                </span>
              </label>
            ))}

            {paymentMethod === "card_mock" && (
              <div className="grid gap-4 rounded-xl bg-slate-50 p-4 sm:grid-cols-3">
                <div className="sm:col-span-3">
                  <label htmlFor="card-number" className={label}>Card number</label>
                  <input
                    id="card-number"
                    inputMode="numeric"
                    placeholder="4242 4242 4242 4242"
                    value={card.number}
                    onChange={(event) =>
                      setCard((c) => ({ ...c, number: event.target.value.replace(/[^\d ]/g, "") }))
                    }
                    className={input}
                  />
                  {errors.card_number && (
                    <p className="mt-1 text-xs text-red-600">{errors.card_number}</p>
                  )}
                </div>
                <div>
                  <label htmlFor="card-expiry" className={label}>Expiry</label>
                  <input
                    id="card-expiry"
                    placeholder="12/28"
                    value={card.expiry}
                    onChange={(event) => setCard((c) => ({ ...c, expiry: event.target.value }))}
                    className={input}
                  />
                  {errors.expiry && <p className="mt-1 text-xs text-red-600">{errors.expiry}</p>}
                </div>
                <div>
                  <label htmlFor="card-cvc" className={label}>CVC</label>
                  <input
                    id="card-cvc"
                    inputMode="numeric"
                    placeholder="123"
                    value={card.cvc}
                    onChange={(event) =>
                      setCard((c) => ({ ...c, cvc: event.target.value.replace(/\D/g, "") }))
                    }
                    className={input}
                  />
                  {errors.cvc && <p className="mt-1 text-xs text-red-600">{errors.cvc}</p>}
                </div>
                <div className="flex items-end text-xs text-slate-400">
                  🔒 Encrypted · test mode
                </div>
                <p className="text-xs leading-relaxed text-slate-500 sm:col-span-3">
                  Mock gateway — no real charge. Test cards:{" "}
                  <span className="font-semibold text-slate-700">4242 4242 4242 4242</span>{" "}
                  succeeds, <span className="font-semibold text-slate-700">4000 0000 0000 0002</span>{" "}
                  is declined.
                </p>
              </div>
            )}
          </div>
        );

      case 6:
        return (
          <div className="space-y-6">
            {/* Items */}
            <section>
              <h3 className="text-sm font-bold uppercase tracking-wide text-slate-900">
                Items ({items.length})
              </h3>
              <ul className="mt-3 space-y-3">
                {items.map((item) => (
                  <li key={item.key} className="flex items-center gap-3">
                    <img
                      src={item.image || IMAGE_FALLBACK}
                      alt=""
                      onError={(event) => {
                        event.currentTarget.src = IMAGE_FALLBACK;
                      }}
                      className="h-14 w-14 rounded-lg border border-slate-200 object-cover"
                    />
                    <span className="flex-1 text-sm">
                      <span className="font-semibold text-slate-900">{item.name}</span>
                      {item.variantName && (
                        <span className="block text-xs text-slate-500">{item.variantName}</span>
                      )}
                    </span>
                    <span className="text-sm text-slate-500">× {item.quantity}</span>
                    <span className="w-24 text-right text-sm font-bold text-slate-900">
                      {formatCurrency(item.price * item.quantity)}
                    </span>
                  </li>
                ))}
              </ul>
            </section>

            {/* Addresses + methods */}
            <section className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-slate-200 p-4 text-sm">
                <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                  Ship to
                </p>
                <p className="mt-1 font-semibold text-slate-900">{customer.first_name} {customer.last_name}</p>
                <p className="text-slate-600">
                  {shippingMode === "saved"
                    ? addresses.find((a) => a.id === shippingAddressId)?.line1
                    : shippingForm.line1}
                  ,{" "}
                  {shippingMode === "saved"
                    ? addresses.find((a) => a.id === shippingAddressId)?.city
                    : shippingForm.city}{" "}
                  {shippingMode === "saved"
                    ? addresses.find((a) => a.id === shippingAddressId)?.postal_code
                    : shippingForm.postal_code}
                </p>
                <p className="text-slate-500">
                  {shippingMode === "saved"
                    ? addresses.find((a) => a.id === shippingAddressId)?.country
                    : shippingForm.country}
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 p-4 text-sm">
                <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                  Delivery & payment
                </p>
                <p className="mt-1 font-semibold text-slate-900">
                  {SHIPPING_METHODS.find((m) => m.id === shippingMethod)?.name} ·{" "}
                  {SHIPPING_METHODS.find((m) => m.id === shippingMethod)?.eta}
                </p>
                <p className="text-slate-600">
                  {paymentMethod === "card_mock" ? "Card (mock gateway)" : "Cash on delivery"}
                </p>
              </div>
            </section>

            {/* Notes */}
            <section>
              <label htmlFor="order-notes" className={label}>
                Order notes (optional)
              </label>
              <textarea
                id="order-notes"
                rows={2}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Delivery instructions, gate codes…"
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
            </section>

            {/* Totals */}
            <section className="rounded-xl bg-slate-50 p-4 text-sm">
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Subtotal</span>
                <span className="font-semibold">{formatCurrency(totals.subtotal)}</span>
              </div>
              {totals.discount > 0 && (
                <div className="flex justify-between py-1 text-emerald-600">
                  <span>Discount ({couponCode})</span>
                  <span className="font-semibold">−{formatCurrency(totals.discount)}</span>
                </div>
              )}
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Shipping</span>
                <span className="font-semibold">
                  {reviewTotals.shipping === 0 ? "FREE" : formatCurrency(reviewTotals.shipping)}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Tax (8%)</span>
                <span className="font-semibold">{formatCurrency(reviewTotals.tax)}</span>
              </div>
              <div className="mt-1 flex justify-between border-t border-slate-200 pt-2 text-base">
                <span className="font-bold text-slate-900">Total</span>
                <span className="font-extrabold text-slate-900">
                  {formatCurrency(reviewTotals.total)}
                </span>
              </div>
            </section>
          </div>
        );

      case 7:
        return (
          <div className="py-4 text-center">
            <div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-emerald-100 text-3xl">
              ✅
            </div>
            <h2 className="mt-4 text-2xl font-extrabold text-slate-900">Thank you!</h2>
            <p className="mt-1 text-slate-500">
              Your order <strong>{placedOrder?.order_number}</strong> has been placed.
            </p>
            <p className="mt-1 text-sm text-slate-500">
              A confirmation email is on its way to{" "}
              <strong>{user?.email}</strong>.
            </p>
            <div className="mx-auto mt-6 max-w-md rounded-xl bg-slate-50 p-4 text-left text-sm">
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Placed</span>
                <span className="font-semibold">{formatDate(placedOrder?.created_at)}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Payment</span>
                <span className="font-semibold capitalize">{placedOrder?.payment_status}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Status</span>
                <span className="font-semibold capitalize">{placedOrder?.status}</span>
              </div>
              <div className="flex justify-between border-t border-slate-200 pt-2 text-base">
                <span className="font-bold text-slate-900">Total</span>
                <span className="font-extrabold text-slate-900">
                  {formatCurrency(placedOrder?.total ?? 0)}
                </span>
              </div>
            </div>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <Link
                to="/account/orders"
                className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700"
              >
                View my orders
              </Link>
              <Link
                to="/products"
                className="rounded-xl border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                Continue shopping
              </Link>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  /* ------------------------------------------------------------------ */
  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="mb-6 text-2xl font-extrabold text-slate-900">Checkout</h1>

      {/* Stepper */}
      <ol className="mb-8 flex gap-1 overflow-x-auto pb-2" aria-label="Checkout progress">
        {STEPS.map((name, index) => {
          const number = index + 1;
          const state = number === step ? "current" : number < step ? "done" : "todo";
          return (
            <li key={name} className="flex items-center">
              <span
                className={`flex items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-bold ${
                  state === "current"
                    ? "bg-brand-600 text-white"
                    : state === "done"
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-slate-100 text-slate-400"
                }`}
              >
                {state === "done" ? "✓" : number}. {name}
              </span>
              {index < STEPS.length - 1 && <span className="mx-1 h-px w-4 bg-slate-200" />}
            </li>
          );
        })}
      </ol>

      <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          {stepContent()}

          {/* Nav */}
          {step < 7 && (
            <div className="mt-8 flex items-center justify-between gap-3 border-t border-slate-100 pt-5">
              <button
                type="button"
                onClick={() => (step === 1 ? navigate("/cart") : setStep(step - 1))}
                className="text-sm font-semibold text-slate-500 transition hover:text-slate-800"
              >
                ← {step === 1 ? "Back to cart" : "Back"}
              </button>
              {step < 6 ? (
                <button
                  type="button"
                  onClick={() => continueTo(step + 1)}
                  className="rounded-xl bg-brand-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700"
                >
                  Continue
                </button>
              ) : (
                <button
                  type="button"
                  onClick={placeOrderNow}
                  disabled={placing}
                  className="rounded-xl bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60"
                >
                  {placing ? "Placing order…" : `Place order · ${formatCurrency(reviewTotals.total)}`}
                </button>
              )}
            </div>
          )}
        </div>

        {/* Sidebar summary */}
        {step < 7 && (
          <aside className="h-fit rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-900">
              Your order
            </h2>
            <ul className="mt-3 space-y-3">
              {items.map((item) => (
                <li key={item.key} className="flex items-center gap-3 text-sm">
                  <span className="relative">
                    <img
                      src={item.image || IMAGE_FALLBACK}
                      alt=""
                      onError={(event) => {
                        event.currentTarget.src = IMAGE_FALLBACK;
                      }}
                      className="h-12 w-12 rounded-lg border border-slate-200 object-cover"
                    />
                    <span className="absolute -right-2 -top-2 grid h-5 min-w-5 place-items-center rounded-full bg-slate-700 px-1 text-[10px] font-bold text-white">
                      {item.quantity}
                    </span>
                  </span>
                  <span className="line-clamp-2 flex-1 text-slate-700">{item.name}</span>
                  <span className="font-semibold text-slate-900">
                    {formatCurrency(item.price * item.quantity)}
                  </span>
                </li>
              ))}
            </ul>
            <dl className="mt-4 space-y-2 border-t border-slate-100 pt-3 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-500">Subtotal</dt>
                <dd className="font-semibold">{formatCurrency(totals.subtotal)}</dd>
              </div>
              {totals.discount > 0 && (
                <div className="flex justify-between text-emerald-600">
                  <dt>Discount</dt>
                  <dd className="font-semibold">−{formatCurrency(totals.discount)}</dd>
                </div>
              )}
              <div className="flex justify-between">
                <dt className="text-slate-500">Shipping</dt>
                <dd className="font-semibold">
                  {reviewTotals.shipping === 0 ? "FREE" : formatCurrency(reviewTotals.shipping)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Tax</dt>
                <dd className="font-semibold">{formatCurrency(reviewTotals.tax)}</dd>
              </div>
              <div className="flex justify-between border-t border-slate-100 pt-2 text-base">
                <dt className="font-bold text-slate-900">Total</dt>
                <dd className="font-extrabold text-slate-900">
                  {formatCurrency(reviewTotals.total)}
                </dd>
              </div>
            </dl>
          </aside>
        )}
      </div>
    </div>
  );
}
