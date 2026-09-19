/**
 * Template metadata for the UI, mirroring backend/app/templates.py.
 * (The backend remains the source of truth; GET /api/templates exposes
 * the same list. Kept static here so the picker renders instantly and
 * the app works even if the backend is briefly unreachable.)
 */

export interface TemplateInfo {
  key: string;
  label: string;
  description: string;
  accentHex: string; // "#rrggbb"
}

export const TEMPLATES: TemplateInfo[] = [
  {
    key: "classic",
    label: "Classic",
    description: "Balanced layout — navy accents, centered header.",
    accentHex: "#1F3B63",
  },
  {
    key: "compact",
    label: "Compact",
    description: "Tighter margins and type — fits the most content.",
    accentHex: "#333333",
  },
  {
    key: "modern",
    label: "Modern",
    description: "Left-aligned header, teal accents, open spacing.",
    accentHex: "#0F766E",
  },
];

export const DEFAULT_TEMPLATE = "classic";

export function getTemplate(key: string | undefined): TemplateInfo {
  return (
    TEMPLATES.find((t) => t.key === key) ??
    TEMPLATES.find((t) => t.key === DEFAULT_TEMPLATE)!
  );
}
