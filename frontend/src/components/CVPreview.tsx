import { getProfile } from "../data/profiles";
import { getTemplate } from "../data/templates";
import type { CVData } from "../types/cv";
import type { ReactNode } from "react";

interface PreviewProps {
  cv: CVData;
}

/**
 * Live A4 preview: mirrors the DOCX output so users see what they get.
 * Section ORDER and HEADINGS follow the active profile — identical to
 * how backend/app/profiles.py drives the generator.
 */
export default function CVPreview({ cv }: PreviewProps) {
  const tpl = getTemplate(cv.template);
  const profile = getProfile(cv.profile);

  const contact = [
    cv.contact.location,
    cv.contact.phone,
    cv.contact.email,
    cv.contact.linkedin,
    cv.contact.github,
    cv.contact.portfolio,
  ]
    .filter(Boolean)
    .join("  |  ");

  // WYSIWYG: the paper shows exactly what the DOCX will contain —
  // no placeholder text that the document itself would not print.
  const isBlank = !cv.name && !cv.professional_title && !contact && !cv.summary;

  if (isBlank) {
    return <p className="ghost">Start typing — your A4 CV appears here.</p>;
  }

  const headingFor: Record<string, string> = {
    summary: profile.key === "fresher" ? "Career Objective" : "Professional Summary",
    skills: "Technical Skills",
    experience: profile.key === "fresher" ? "Internships / Part-time Work" : "Professional Experience",
    projects: "Selected Projects",
    education: "Education",
    certifications: "Certifications / Additional Training",
    languages: "Languages",
    additional_info: "Additional Information",
  };

  const sectionBody: Record<string, ReactNode> = {
    summary: cv.summary ? <p>{cv.summary}</p> : null,
    skills:
      cv.skills.flatMap((g) => g.items).length > 0 ? (
        <>
          {cv.skills.map((group, i) => (
            <p key={i}>
              {group.category ? (
                <>
                  <b>{group.category}: </b>
                </>
              ) : null}
              {group.items.join(", ")}
            </p>
          ))}
        </>
      ) : null,
    experience:
      cv.experience.length > 0 ? (
        <>
          {cv.experience.map((job, i) => {
            const headline = [job.title, job.company].filter(Boolean).join("  |  ");
            const meta = [job.location, job.dates].filter(Boolean).join("  |  ");
            return (
              <div key={i} className="pv-entry">
                <p>
                  <b>{headline}</b>
                  {meta ? (
                    <>
                      <br />
                      <i>{meta}</i>
                    </>
                  ) : null}
                </p>
                {job.bullets.length > 0 ? (
                  <ul>
                    {job.bullets.map((b, j) => (
                      <li key={j}>{b}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            );
          })}
        </>
      ) : null,
    projects:
      cv.projects.length > 0 ? (
        <>
          {cv.projects.map((p, i) => (
            <div key={i} className="pv-entry">
              <p>
                <b>{p.name}</b>
                {p.technologies.length > 0 ? (
                  <i>  |  {p.technologies.join(", ")}</i>
                ) : null}
              </p>
              {p.description ? <p>{p.description}</p> : null}
              {p.details.length > 0 ? (
                <ul>
                  {p.details.map((d, j) => (
                    <li key={j}>{d}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ))}
        </>
      ) : null,
    education:
      cv.education.length > 0 ? (
        <>
          {cv.education.map((edu, i) => {
            const headline = [edu.degree, edu.school].filter(Boolean).join("  |  ");
            const meta = [edu.location, edu.dates].filter(Boolean).join("  |  ");
            return (
              <div key={i} className="pv-entry">
                <p>
                  <b>{headline}</b>
                  {meta ? (
                    <>
                      <br />
                      <i>{meta}</i>
                    </>
                  ) : null}
                </p>
                {edu.details.length > 0 ? (
                  <ul>
                    {edu.details.map((d, j) => (
                      <li key={j}>{d}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            );
          })}
        </>
      ) : null,
    certifications:
      cv.certifications.length > 0 ? (
        <ul>
          {cv.certifications.map((c, i) => (
            <li key={i}>
              {[c.title, c.issuer].filter(Boolean).join(" - ")}
              {c.date ? ` (${c.date})` : ""}
            </li>
          ))}
        </ul>
      ) : null,
    languages:
      cv.languages.length > 0 ? <p>{cv.languages.join(", ")}</p> : null,
    additional_info:
      cv.additional_info.length > 0 ? (
        <ul>
          {cv.additional_info.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      ) : null,
  };

  return (
    <div
      className={`paper-inner ${tpl.key === "modern" ? "tpl-modern" : ""} ${tpl.key === "compact" ? "tpl-compact" : ""}`}
      style={{ "--tpl-accent": tpl.accentHex } as React.CSSProperties}
    >
      {cv.name ? <div className="pv-name">{cv.name}</div> : null}
      {cv.professional_title ? <div className="pv-title">{cv.professional_title}</div> : null}
      {contact ? <div className="pv-contact">{contact}</div> : null}

      {/* Sections in PROFILE order — mirrors the generator's section_order */}
      {profile.sectionOrder.map((section) => {
        const body = sectionBody[section];
        if (!body) return null;
        return (
          <div key={section}>
            <h3>{headingFor[section]}</h3>
            {body}
          </div>
        );
      })}
    </div>
  );
}

/** ATS readiness checklist shown above the paper preview.
 *
 * Mirrors the backend scorer's core rules (same email shape, phone =
 * 7-15 digits ignoring date ranges, >=3 skills, every job needs bullets)
 * so the live checklist never contradicts /api/score-cv.
 */
export function ATSChecks({ cv }: { cv: CVData }) {
  const emailRe = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  const digits = (cv.contact.phone.match(/\d/g) ?? []).length;
  const phoneOk = digits >= 7 && digits <= 15;
  const skillCount = cv.skills.flatMap((g) => g.items).length;
  const fresher = getProfile(cv.profile).key === "fresher";
  const checks = [
    { ok: true, label: "Single-column · real text, no graphics" },
    { ok: cv.name.trim().length >= 2, label: "Name present" },
    { ok: emailRe.test(cv.contact.email.trim()), label: "Valid email" },
    { ok: phoneOk, label: "Phone present (7–15 digits)" },
    // Mode-aware: fresher CVs are judged on projects, not jobs.
    fresher
      ? { ok: cv.projects.length > 0, label: "At least 1 project" }
      : { ok: cv.experience.length > 0, label: "At least 1 job" },
    fresher
      ? {
          ok:
            cv.projects.length > 0 && cv.projects.every((p) => p.details.length > 0),
          label: "Every project has bullets",
        }
      : {
          ok:
            cv.experience.length > 0 && cv.experience.every((e) => e.bullets.length > 0),
          label: "Every job has bullets",
        },
    {
      ok: skillCount >= 3,
      label: `${skillCount} skill keyword${skillCount === 1 ? "" : "s"}`,
    },
  ];

  // Not a live region: it re-renders on every keystroke, which would make
  // screen readers announce the whole checklist constantly. It sits above
  // the preview in reading order, so users can find it by browsing.
  return (
    <div className="ats">
      {checks.map((c, i) => (
        <div className={`ats-item ${c.ok ? "pass" : "fail"}`} key={i}>
          <span className="ic">{c.ok ? "✓" : "○"}</span>
          <span>{c.label}</span>
        </div>
      ))}
    </div>
  );
}
