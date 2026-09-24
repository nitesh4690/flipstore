import Modal from "./Modal.jsx";

/**
 * Confirmation dialog built on Modal (destructive actions).
 */
export default function ConfirmDialog({
  open,
  title = "Are you sure?",
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  onCancel,
  danger = false,
}) {
  return (
    <Modal open={open} onClose={onCancel} title={title}>
      {message && <p className="text-sm text-slate-600">{message}</p>}
      <div className="mt-6 flex justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          {cancelLabel}
        </button>
        <button
          type="button"
          onClick={onConfirm}
          className={`rounded-xl px-4 py-2 text-sm font-semibold text-white transition ${
            danger
              ? "bg-red-600 hover:bg-red-700"
              : "bg-brand-600 hover:bg-brand-700"
          }`}
        >
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
