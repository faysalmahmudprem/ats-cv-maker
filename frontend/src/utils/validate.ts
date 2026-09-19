import type { CVData } from "../types/cv";
import { getProfile } from "../data/profiles";

/** Simple email rule shared with the backend: something@something.tld */
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export interface CVProblems {
  name: string;
  professional_title: string;
  email: string;
  phone: string;
  experience: string;
  projects: string;
}

/** Returns a problem message per field; empty string means the field is OK.
 *
 * Hard requirements only — these BLOCK the download. Missing achievement
 * bullets are deliberately NOT here: blocking a user at the final step
 * after ten minutes of typing is the worst moment to lose them. Bullet
 * gaps are surfaced as non-blocking cautions (see cvWarnings).
 */
export function validateCV(cv: CVData): CVProblems {
  const problems: CVProblems = {
    name: "",
    professional_title: "",
    email: "",
    phone: "",
    experience: "",
    projects: "",
  };

  if (cv.name.trim().length < 2) {
    problems.name = "Please enter your full name.";
  }
  if (!cv.professional_title.trim()) {
    problems.professional_title = "Please enter a job title.";
  }
  if (!cv.contact.email.trim()) {
    problems.email = "Please enter your email address.";
  } else if (!EMAIL_RE.test(cv.contact.email)) {
    problems.email = "Please enter a valid email address.";
  }
  if (!cv.contact.phone.trim()) {
    problems.phone = "Please enter a phone number.";
  }

  const profile = getProfile(cv.profile);

  if (profile.key === "fresher") {
    // Fresher mode: projects are the hero; experience becomes optional.
    if (cv.projects.length === 0) {
      problems.projects = "Add at least one project — this is the heart of an entry-level CV.";
    }
  } else if (cv.experience.length === 0) {
    problems.experience = "Please add at least one work experience entry.";
  }

  return problems;
}

export interface CVWarnings {
  experience: string;
  projects: string;
}

/**
 * Non-blocking quality cautions. A CV with bulletless entries is thin,
 * not invalid — the user can still download, with honest advice shown
 * in the review card instead of a hard error.
 */
export function cvWarnings(cv: CVData): CVWarnings {
  const warnings: CVWarnings = { experience: "", projects: "" };
  const profile = getProfile(cv.profile);

  if (profile.key === "fresher") {
    if (cv.projects.length > 0 && cv.projects.some((p) => p.details.length === 0)) {
      warnings.projects = "Each project reads stronger with at least one detail bullet.";
    }
    if (cv.experience.length > 0 && cv.experience.some((e) => e.bullets.length === 0)) {
      warnings.experience = "Internships without achievement bullets look thin — add one if you can.";
    }
  } else if (cv.experience.length > 0 && cv.experience.some((e) => e.bullets.length === 0)) {
    warnings.experience = "Each job reads stronger with at least one achievement bullet.";
  }

  return warnings;
}

/** True when no field has a problem. */
export function isCVValid(problems: CVProblems): boolean {
  return Object.values(problems).every((p) => p === "");
}

/**
 * One tick item per editor card. Ticks flip per profile:
 * - "experience": experienced requires an entry; fresher shows "Optional ✓".
 * - "projects":   fresher requires one; experienced shows "Optional ✓" when empty.
 */
export function sectionTicks(cv: CVData): Record<string, boolean> {
  const profile = getProfile(cv.profile);
  const hasBulleted = (xs: { bullets?: string[]; details?: string[] }[]) =>
    xs.length > 0 && xs.every((x) => (x.bullets ?? x.details ?? []).length > 0);

  return {
    personal:
      cv.name.trim().length >= 2 &&
      !!cv.professional_title.trim() &&
      EMAIL_RE.test(cv.contact.email) &&
      !!cv.contact.phone.trim(),
    summary: cv.summary.trim().length > 0,
    skills: cv.skills.length > 0 && cv.skills.every((s) => s.items.length > 0),
    experience: profile.key === "fresher" ? cv.experience.length === 0 || hasBulleted(cv.experience) : hasBulleted(cv.experience),
    projects: profile.key === "fresher" ? hasBulleted(cv.projects) : cv.projects.length === 0 || hasBulleted(cv.projects),
    education: cv.education.length > 0 && cv.education.every((e) => e.degree.trim() !== "" && e.school.trim() !== ""),
    extras: cv.certifications.length > 0 || cv.languages.length > 0 || cv.additional_info.length > 0,
  };
}
