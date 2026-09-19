/**
 * Small, reusable UI primitives shared by every form section:
 * floating-label fields, buttons, section cards, tag input, bullets input.
 * Keeping them here makes the section components short and readable.
 */
import { useId, useRef, useState, type ChangeEvent, type ReactNode } from "react";

// ---------- Fields ----------

interface FieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
  maxLength?: number;
  required?: boolean;
  error?: string;
  autoComplete?: string;
  inputMode?: "text" | "url" | "tel" | "email";
}

export function Field({
  label,
  value,
  onChange,
  type = "text",
  placeholder = " ",
  maxLength,
  required,
  error,
  autoComplete,
  inputMode,
}: FieldProps) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className="field-wrap">
      <label className="field" htmlFor={id}>
        <input
          id={id}
          type={type}
          value={value}
          placeholder={placeholder}
          maxLength={maxLength}
          autoComplete={autoComplete}
          inputMode={inputMode}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
        />
        <span>
          {label}
          {required ? " *" : ""}
        </span>
      </label>
      {error ? (
        <p className="field-error" id={errorId} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

interface TextAreaFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  rows?: number;
  maxLength?: number;
  hint?: string;
}

export function TextAreaField({
  label,
  value,
  onChange,
  rows = 4,
  maxLength,
  hint,
}: TextAreaFieldProps) {
  const id = useId();
  return (
    <div className="field-wrap">
      <label className="field" htmlFor={id}>
        <textarea
          id={id}
          rows={rows}
          value={value}
          maxLength={maxLength}
          placeholder=" "
          onChange={(e: ChangeEvent<HTMLTextAreaElement>) => onChange(e.target.value)}
        />
        <span>{label}</span>
      </label>
      {hint ? <p className="field-hint">{hint}</p> : null}
    </div>
  );
}

// ---------- Bullets (one input per bullet) ----------

interface BulletsInputProps {
  label: string;
  bullets: string[];
  onChange: (bullets: string[]) => void;
  /** Hint shown on the first empty row / empty state. */
  placeholder?: string;
  addLabel?: string;
}

/**
 * One input row per bullet — clearer than a "one per line" textarea for
 * non-technical users. Rows stay put while typing; on blur the list is
 * trimmed of empty rows. Enter adds a new bullet right below the current
 * one and focuses it.
 */
export function BulletsInput({
  label,
  bullets,
  onChange,
  placeholder,
  addLabel = "+ Add bullet",
}: BulletsInputProps) {
  const rowRefs = useRef<(HTMLInputElement | null)[]>([]);

  function updateAt(index: number, value: string) {
    onChange(bullets.map((b, i) => (i === index ? value : b)));
  }

  function removeAt(index: number) {
    onChange(bullets.filter((_, i) => i !== index));
  }

  function addAfter(index: number) {
    const next = [...bullets];
    next.splice(index + 1, 0, "");
    onChange(next);
    // Focus the new row after React commits it.
    requestAnimationFrame(() => rowRefs.current[index + 1]?.focus());
  }

  function addAtEnd() {
    onChange([...bullets, ""]);
    requestAnimationFrame(() => rowRefs.current[bullets.length]?.focus());
  }

  // Tidy the list when a row loses focus: trim text, drop empty rows.
  function normalize() {
    const cleaned = bullets.map((b) => b.trim()).filter(Boolean);
    if (cleaned.length !== bullets.length) {
      onChange(cleaned);
    } else if (bullets.some((b) => b !== b.trim())) {
      onChange(cleaned);
    }
  }

  return (
    <div className="field-wrap">
      <span className="inline-label">{label}</span>
      <div className="bullets-list">
        {bullets.length === 0 ? (
          <p className="field-hint">{placeholder ?? "No bullets yet — add the first one below."}</p>
        ) : (
          bullets.map((bullet, i) => (
            <div className="bullet-row" key={i}>
              <span className="bullet-dot" aria-hidden="true">
                •
              </span>
              <input
                ref={(el) => {
                  rowRefs.current[i] = el;
                }}
                type="text"
                value={bullet}
                maxLength={300}
                aria-label={`${label} — bullet ${i + 1}`}
                placeholder={i === 0 ? (placeholder ?? "e.g. Led a team of five") : ""}
                onChange={(e) => updateAt(i, e.target.value)}
                onBlur={normalize}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addAfter(i);
                  }
                }}
              />
              <button
                type="button"
                className="tool rm-bullet"
                aria-label={`Remove bullet ${i + 1}`}
                onClick={() => removeAt(i)}
              >
                ×
              </button>
            </div>
          ))
        )}
      </div>
      <button type="button" className="add-bullet" onClick={addAtEnd}>
        {addLabel}
      </button>
    </div>
  );
}

// ---------- Tag input (skills) ----------

interface TagInputProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  maxTags?: number;
  maxTagLength?: number;
}

export function TagInput({
  tags,
  onChange,
  placeholder = "Type and press Enter",
  maxTags = 40,
  maxTagLength = 60,
}: TagInputProps) {
  const [draft, setDraft] = useState("");

  function commit() {
    const value = draft.trim().replace(/,+$/, "");
    if (!value || tags.includes(value) || tags.length >= maxTags) return;
    onChange([...tags, value.slice(0, maxTagLength)]);
    setDraft("");
  }

  function remove(index: number) {
    onChange(tags.filter((_, i) => i !== index));
  }

  return (
    <div className="tagbox">
      <div className="tags" aria-live="polite">
        {tags.map((tag, i) => (
          <span className="tag" key={`${tag}-${i}`}>
            <span>{tag}</span>
            <button
              type="button"
              aria-label={`Remove ${tag}`}
              onClick={() => remove(i)}
            >
              ×
            </button>
          </span>
        ))}
      </div>
      <input
        value={draft}
        placeholder={placeholder}
        aria-label="Add a skill"
        maxLength={maxTagLength}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            commit();
          } else if (e.key === "Backspace" && !draft && tags.length > 0) {
            remove(tags.length - 1);
          }
        }}
        onBlur={commit}
      />
    </div>
  );
}

// ---------- Buttons & cards ----------

interface BtnProps {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "soft" | "ghost";
  size?: "md" | "lg";
  type?: "button" | "submit";
  disabled?: boolean;
  loading?: boolean;
  className?: string;
  ariaLabel?: string;
}

export function Btn({
  children,
  onClick,
  variant = "primary",
  size = "md",
  type = "button",
  disabled,
  loading,
  className = "",
  ariaLabel,
}: BtnProps) {
  return (
    <button
      type={type}
      className={`btn btn-${variant} ${size === "lg" ? "btn-lg" : ""} ${loading ? "loading" : ""} ${className}`}
      onClick={onClick}
      disabled={disabled || loading}
      aria-label={ariaLabel}
    >
      {children}
      {loading ? <span className="spinner" aria-hidden="true" /> : null}
    </button>
  );
}

interface SectionCardProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  /** DOM id for the section nav's scrollspy + click-to-jump. */
  id?: string;
}

export function SectionCard({ title, subtitle, actions, children, id }: SectionCardProps) {
  return (
    <section className="card" id={id}>
      <div className="card-head">
        <div>
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        {actions ? <div className="card-actions">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function EntryCard({
  title,
  onRemove,
  onMoveUp,
  onMoveDown,
  first,
  last,
  children,
}: {
  title: string;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  first: boolean;
  last: boolean;
  children: ReactNode;
}) {
  return (
    <div className="entry">
      <div className="entry-top">
        <strong>{title}</strong>
        <div className="entry-tools">
          <button
            type="button"
            className="tool"
            onClick={onMoveUp}
            disabled={first}
            aria-label={`Move ${title} up`}
          >
            ↑
          </button>
          <button
            type="button"
            className="tool"
            onClick={onMoveDown}
            disabled={last}
            aria-label={`Move ${title} down`}
          >
            ↓
          </button>
          <button type="button" className="rm" onClick={onRemove}>
            Remove
          </button>
        </div>
      </div>
      {children}
    </div>
  );
}

export function EmptyState({ text, action }: { text: string; action: ReactNode }) {
  return (
    <div className="empty">
      <p>{text}</p>
      {action}
    </div>
  );
}
