/**
 * CV data types — mirror the backend Pydantic schemas (backend/app/schemas/cv.py)
 * so both sides of the API speak the same language.
 */

export interface Contact {
  location: string;
  phone: string;
  email: string;
  linkedin: string;
  github: string;
  portfolio: string;
}

export interface SkillGroup {
  category: string;
  items: string[];
}

export interface Experience {
  title: string;
  company: string;
  location: string;
  dates: string;
  bullets: string[];
}

export interface Project {
  name: string;
  technologies: string[];
  description: string;
  details: string[];
}

export interface Education {
  degree: string;
  school: string;
  location: string;
  dates: string;
  details: string[];
}

export interface Certification {
  title: string;
  issuer: string;
  date: string;
}

export interface CVData {
  /** Profile key — "experienced" | "fresher" (see src/data/profiles.ts). */
  profile: string;
  /** Template key — must match a backend template (see src/data/templates.ts). */
  template: string;
  name: string;
  professional_title: string;
  contact: Contact;
  summary: string;
  skills: SkillGroup[];
  experience: Experience[];
  projects: Project[];
  education: Education[];
  certifications: Certification[];
  languages: string[];
  additional_info: string[];
}

/** Factories for empty entries — keeps "add" buttons one-liners. */

export function emptyCV(): CVData {
  return {
    profile: "experienced",
    template: "classic",
    name: "",
    professional_title: "",
    contact: {
      location: "",
      phone: "",
      email: "",
      linkedin: "",
      github: "",
      portfolio: "",
    },
    summary: "",
    skills: [],
    experience: [],
    projects: [],
    education: [],
    certifications: [],
    languages: [],
    additional_info: [],
  };
}

export function emptyExperience(): Experience {
  return { title: "", company: "", location: "", dates: "", bullets: [] };
}

export function emptyProject(): Project {
  return { name: "", technologies: [], description: "", details: [] };
}

export function emptyEducation(): Education {
  return { degree: "", school: "", location: "", dates: "", details: [] };
}

export function emptyCertification(): Certification {
  return { title: "", issuer: "", date: "" };
}
