/**
 * Sticky mini-nav: one tick per editor section, click-to-jump, and the
 * current section highlighted while scrolling (scrollspy). Gives users a
 * sense of place and progress in what is otherwise a long form.
 */
import { useEffect, useState } from "react";
import { getProfile } from "../data/profiles";
import type { CVData } from "../types/cv";
import { sectionTicks } from "../utils/validate";
import { Btn } from "./ui";

/** Editor card anchors — must match the ids used in App.tsx. */
export const SECTION_IDS = {
  profile: "sec-profile",
  personal: "sec-personal",
  summary: "sec-summary",
  skills: "sec-skills",
  experience: "sec-experience",
  projects: "sec-projects",
  education: "sec-education",
  extras: "sec-extras",
  template: "sec-template",
  review: "sec-review",
} as const;

interface NavItem {
  id: string;
  label: string;
  tickKey: keyof ReturnType<typeof sectionTicks> | null;
}

/** Nav items in display order; middle sections follow the active profile. */
export function navItemsFor(cv: CVData): NavItem[] {
  const profile = getProfile(cv.profile);
  const labelFor: Record<string, string> = {
    experience: profile.key === "fresher" ? "Internships" : "Experience",
    projects: "Projects",
    education: "Education",
  };
  const items: NavItem[] = [
    { id: SECTION_IDS.profile, label: "Start", tickKey: null },
    { id: SECTION_IDS.personal, label: "Personal", tickKey: "personal" },
    { id: SECTION_IDS.summary, label: "Summary", tickKey: "summary" },
    { id: SECTION_IDS.skills, label: "Skills", tickKey: "skills" },
  ];
  for (const section of profile.middleSections) {
    items.push({
      id: SECTION_IDS[section],
      label: labelFor[section],
      tickKey: section,
    });
  }
  items.push(
    { id: SECTION_IDS.extras, label: "Extras", tickKey: "extras" },
    { id: SECTION_IDS.template, label: "Style", tickKey: null },
    { id: SECTION_IDS.review, label: "Download", tickKey: null },
  );
  return items;
}

export function scrollToSection(id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "start" });
  // Move keyboard/screen-reader focus to the target card, not just the
  // viewport — otherwise focus stays behind and Tab jumps back up.
  const heading = el.querySelector<HTMLElement>("h2");
  const target = heading ?? el;
  if (!heading) target.setAttribute("tabindex", "-1");
  target.focus({ preventScroll: true });
}

export default function SectionNav({ cv }: { cv: CVData }) {
  const items = navItemsFor(cv);
  const ticks = sectionTicks(cv);
  const [active, setActive] = useState(items[0]?.id ?? "");

  // Scrollspy: highlight the card currently closest to the top.
  // Keyed on the section list itself (not a derived count) so a profile
  // switch that changes which sections exist always re-observes.
  const itemIds = items.map((i) => i.id).join(" ");
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActive(entry.target.id);
        }
      },
      { rootMargin: "-30% 0px -60% 0px" },
    );
    for (const id of itemIds.split(" ")) {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [itemIds]);

  return (
    <nav className="section-nav" aria-label="Editor progress">
      <div className="section-nav-inner">
        {items.map((item) => {
          const done = item.tickKey !== null && ticks[item.tickKey];
          return (
            <button
              key={item.id}
              type="button"
              className={`sec-link ${active === item.id ? "current" : ""}`}
              onClick={() => scrollToSection(item.id)}
              aria-current={active === item.id ? "true" : undefined}
            >
              <i className={`tick ${done ? "done" : ""}`} aria-hidden="true">
                {done ? "✓" : ""}
              </i>
              {item.label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}

/** "Next section" button placed at the bottom of each editor card. */
export function NextSection({
  targetId,
  label,
}: {
  targetId: string;
  label: string;
}) {
  return (
    <div className="next-row">
      <Btn variant="ghost" onClick={() => scrollToSection(targetId)}>
        Next: {label} ↓
      </Btn>
    </div>
  );
}
