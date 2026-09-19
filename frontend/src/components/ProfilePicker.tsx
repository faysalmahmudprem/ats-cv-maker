/**
 * Profile picker: Experienced vs Fresher/Entry-level.
 * A profile changes document STRUCTURE (section order, headings) —
 * templates change presentation. Mirrors backend/app/profiles.py.
 *
 * Rendered as toggle buttons with aria-pressed rather than a fake
 * radiogroup: buttons with role="radio" would promise arrow-key
 * navigation that click-only buttons can't deliver.
 */
import { PROFILES, type ProfileKey } from "../data/profiles";

interface Props {
  value: ProfileKey;
  onChange: (key: ProfileKey) => void;
}

export default function ProfilePicker({ value, onChange }: Props) {
  return (
    <div className="profile-grid" aria-label="CV profile">
      {PROFILES.map((p) => {
        const selected = p.key === value;
        return (
          <button
            key={p.key}
            type="button"
            aria-pressed={selected}
            className={`profile-card ${selected ? "selected" : ""}`}
            onClick={() => onChange(p.key)}
          >
            <span className="profile-head">
              <span className="profile-name">{p.label}</span>
              <span className={`radio ${selected ? "on" : ""}`} aria-hidden="true" />
            </span>
            <span className="profile-caption">{p.caption}</span>
            <span className="profile-bullets">
              {p.bullets.map((b) => (
                <span className="profile-bullet" key={b}>
                  {b}
                </span>
              ))}
            </span>
          </button>
        );
      })}
    </div>
  );
}
