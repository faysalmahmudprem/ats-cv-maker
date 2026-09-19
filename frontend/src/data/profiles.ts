/**
 * Profile metadata for the UI, mirroring backend/app/profiles.py.
 * A profile changes document STRUCTURE (section order + headings);
 * templates change presentation. The backend stays the source of truth.
 */

export type ProfileKey = "experienced" | "fresher";

export interface ProfileInfo {
  key: ProfileKey;
  label: string;
  caption: string;
  /** Editor card order after Personal/Summary, before Template/Review. */
  middleSections: Array<"experience" | "projects" | "education" | "extras">;
  /** Full DOCX section order — mirrors backend profiles.section_order. */
  sectionOrder: Array<
    "summary" | "skills" | "experience" | "projects" | "education" | "certifications" | "languages" | "additional_info"
  >;
  /** Short bullet shown on the toggle cards. */
  bullets: string[];
}

export const PROFILES: ProfileInfo[] = [
  {
    key: "experienced",
    label: "Experienced",
    caption: "Work experience leads your CV.",
    middleSections: ["experience", "projects", "education", "extras"],
    sectionOrder: [
      "summary",
      "skills",
      "experience",
      "projects",
      "education",
      "certifications",
      "languages",
      "additional_info",
    ],
    bullets: [
      "Jobs with achievements up top",
      "Best for 1+ years of work",
    ],
  },
  {
    key: "fresher",
    label: "Fresher / Entry-level",
    caption: "Education and projects lead your CV.",
    middleSections: ["education", "projects", "experience", "extras"],
    sectionOrder: [
      "summary",
      "education",
      "projects",
      "skills",
      "experience",
      "certifications",
      "languages",
      "additional_info",
    ],
    bullets: [
      "Education & projects up top",
      "Experience becomes optional",
    ],
  },
];

export const DEFAULT_PROFILE: ProfileKey = "experienced";

export function getProfile(key: string | undefined): ProfileInfo {
  return (
    PROFILES.find((p) => p.key === key) ??
    PROFILES.find((p) => p.key === DEFAULT_PROFILE)!
  );
}
