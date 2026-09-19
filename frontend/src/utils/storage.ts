/**
 * Draft autosave in localStorage.
 *
 * The editor holds a lot of typing; losing it to an accidental refresh or
 * tab close is the worst thing this product can do to a user. The draft
 * is saved debounced (~500ms after the last keystroke) and restored with
 * a banner the user must accept — never silently.
 */
import { emptyCV, type CVData } from "../types/cv";

const STORAGE_KEY = "cv_draft_v1";
const SCHEMA_VERSION = 1;

export function saveDraft(cv: CVData): void {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ version: SCHEMA_VERSION, cv, savedAt: Date.now() }),
    );
  } catch {
    // Private mode / storage full — autosave is best-effort, never fatal.
  }
}

/** Returns the saved draft only if it exists and looks like our schema. */
export function loadDraft(): CVData | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { version?: number; cv?: CVData };
    if (parsed.version !== SCHEMA_VERSION || typeof parsed.cv !== "object" || parsed.cv === null) {
      return null;
    }
    // Merge over an empty CV so fields added later default cleanly.
    const base = emptyCV();
    const cv = { ...base, ...parsed.cv, contact: { ...base.contact, ...parsed.cv.contact } };
    return hasContent(cv) ? cv : null;
  } catch {
    return null;
  }
}

export function clearDraft(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export function draftAgeMinutes(savedAt: number): number {
  return Math.max(0, Math.round((Date.now() - savedAt) / 60000));
}

/** True when the user has entered anything worth saving. */
export function hasContent(cv: CVData): boolean {
  return (
    cv.name.trim() !== "" ||
    cv.professional_title.trim() !== "" ||
    Object.values(cv.contact).some((v) => v.trim() !== "") ||
    cv.summary.trim() !== "" ||
    cv.skills.length > 0 ||
    cv.experience.length > 0 ||
    cv.projects.length > 0 ||
    cv.education.length > 0 ||
    cv.certifications.length > 0 ||
    cv.languages.length > 0 ||
    cv.additional_info.length > 0
  );
}
