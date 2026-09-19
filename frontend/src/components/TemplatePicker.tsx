import classicThumb from "../assets/templates/classic.png";
import compactThumb from "../assets/templates/compact.png";
import modernThumb from "../assets/templates/modern.png";
import { TEMPLATES } from "../data/templates";

/**
 * PNG previews of page 1 of each template's real DOCX output.
 * Regenerate with: cd backend && python scripts/generate_template_previews.py
 * Templates without a thumbnail fall back to the accent-color swatch.
 */
const THUMBS: Record<string, string> = {
  classic: classicThumb,
  compact: compactThumb,
  modern: modernThumb,
};

interface Props {
  value: string;
  onChange: (key: string) => void;
}

/**
 * Template chooser rendered as radio cards (single selection, keyboard
 * friendly — arrow keys work within the group).
 */
export default function TemplatePicker({ value, onChange }: Props) {
  return (
    <div className="tpl-grid" role="radiogroup" aria-label="CV template">
      {TEMPLATES.map((t) => {
        const selected = t.key === value;
        const thumb = THUMBS[t.key];
        return (
          <label
            key={t.key}
            className={`tpl-card ${selected ? "selected" : ""}`}
          >
            <input
              type="radio"
              name="template"
              value={t.key}
              checked={selected}
              onChange={() => onChange(t.key)}
            />
            {thumb ? (
              <img
                src={thumb}
                alt=""
                aria-hidden="true"
                className="tpl-thumb"
                loading="lazy"
              />
            ) : (
              <span
                className="tpl-swatch"
                style={{ background: t.accentHex }}
                aria-hidden="true"
              />
            )}
            <span className="tpl-info">
              <span className="tpl-label">
                {t.label}
                {selected ? <span className="tpl-check" aria-hidden="true"> ✓</span> : null}
              </span>
              <span className="tpl-desc">{t.description}</span>
            </span>
          </label>
        );
      })}
    </div>
  );
}
