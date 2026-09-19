export type StatusKind = "idle" | "loading" | "success" | "error";

export default function StatusBanner({
  status,
  message,
}: {
  status: StatusKind;
  message: string;
}) {
  if (status === "idle" || !message) return null;

  return (
    <div
      className={`status-banner ${status}`}
      role={status === "error" ? "alert" : "status"}
      aria-live="polite"
    >
      <span className="status-icon" aria-hidden="true">
        {status === "loading" ? "⏳" : status === "success" ? "✓" : "✕"}
      </span>
      <span>{message}</span>
    </div>
  );
}
