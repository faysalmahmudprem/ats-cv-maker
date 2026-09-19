import { describe, expect, it } from "vitest";
import { cvWarnings, isCVValid, sectionTicks, validateCV } from "./validate";
import { emptyCV, type CVData } from "../types/cv";

// ---- Fixtures -------------------------------------------------------------

function validExperienced(): CVData {
  const cv = emptyCV();
  cv.name = "Alex Example";
  cv.professional_title = "Software Engineer";
  cv.contact.email = "alex@example.com";
  cv.contact.phone = "+880 1000-000000";
  cv.experience = [
    {
      title: "Software Engineer",
      company: "Example Corp",
      location: "Dhaka",
      dates: "Jan 2024 - Present",
      bullets: ["Built REST APIs serving 10k daily requests."],
    },
  ];
  return cv;
}

function validFresher(): CVData {
  const cv = validExperienced();
  cv.profile = "fresher";
  cv.experience = [];
  cv.projects = [
    { name: "Campus App", technologies: [], description: "", details: ["Built the registration flow."] },
  ];
  return cv;
}

// ---- validateCV ------------------------------------------------------------

describe("validateCV", () => {
  it("flags every required field on an empty CV (experienced profile)", () => {
    const p = validateCV(emptyCV());
    expect(p.name).toMatch(/name/i);
    expect(p.professional_title).toMatch(/title/i);
    expect(p.email).toMatch(/email/i);
    expect(p.phone).toMatch(/phone/i);
    expect(p.experience).toMatch(/experience/i);
    // Projects are optional in experienced mode.
    expect(p.projects).toBe("");
  });

  it("accepts a complete experienced CV", () => {
    expect(isCVValid(validateCV(validExperienced()))).toBe(true);
  });

  it("no longer requires bullets to download (softened gate)", () => {
    const cv = validExperienced();
    cv.experience[0].bullets = [];
    expect(validateCV(cv).experience).toBe("");
    expect(isCVValid(validateCV(cv))).toBe(true);
  });

  it("rejects a whitespace-only name but accepts a 2-char name", () => {
    const cv = validExperienced();
    cv.name = "   ";
    expect(validateCV(cv).name).not.toBe("");
    cv.name = "Li";
    expect(validateCV(cv).name).toBe("");
  });

  it("rejects malformed emails and accepts a realistic one", () => {
    const cv = validExperienced();
    for (const bad of ["plainaddress", "a@b", "a b@c.com", "user@domain."]) {
      cv.contact.email = bad;
      expect(validateCV(cv).email).not.toBe("");
    }
    cv.contact.email = "first.last+tag@sub.domain.co";
    expect(validateCV(cv).email).toBe("");
  });

  it("rejects a whitespace-only phone", () => {
    const cv = validExperienced();
    cv.contact.phone = "   ";
    expect(validateCV(cv).phone).not.toBe("");
  });

  it("bulletless jobs no longer block download — they surface as cautions", () => {
    const cv = validExperienced();
    cv.experience[0].bullets = [];
    expect(validateCV(cv).experience).toBe("");
    expect(cvWarnings(cv).experience).toMatch(/bullet/i);
  });

  it("fresher mode: projects required, experience optional — bullets are cautions only", () => {
    const cv = validFresher();

    // No projects -> problem; no experience -> fine.
    cv.projects = [];
    let p = validateCV(cv);
    expect(p.projects).toMatch(/project/i);
    expect(p.experience).toBe("");

    // Project without bullets -> downloadable, but cautioned.
    cv.projects = [{ name: "App", technologies: [], description: "", details: [] }];
    p = validateCV(cv);
    expect(p.projects).toBe("");

    // Present-but-bulletless experience -> downloadable, but cautioned.
    cv.projects = [{ name: "App", technologies: [], description: "", details: ["x"] }];
    cv.experience = [{ title: "Intern", company: "C", location: "", dates: "", bullets: [] }];
    expect(validateCV(cv).experience).toBe("");

    // Complete fresher CV passes.
    expect(isCVValid(validateCV(validFresher()))).toBe(true);
  });

  it("isCVValid mirrors the problem list", () => {
    expect(isCVValid(validateCV(emptyCV()))).toBe(false);
  });
});

// ---- cvWarnings ------------------------------------------------------------

describe("cvWarnings", () => {
  it("warns when an experienced CV has a bulletless job", () => {
    const cv = validExperienced();
    cv.experience[0].bullets = [];
    expect(cvWarnings(cv).experience).toMatch(/bullet/i);
    expect(cvWarnings(cv).projects).toBe("");
  });

  it("no warning when every job has bullets", () => {
    expect(cvWarnings(validExperienced()).experience).toBe("");
  });

  it("fresher: warns on bulletless projects and internships", () => {
    const cv = validFresher();
    cv.projects[0].details = [];
    cv.experience = [{ title: "Intern", company: "C", location: "", dates: "", bullets: [] }];
    const w = cvWarnings(cv);
    expect(w.projects).toMatch(/bullet/i);
    expect(w.experience).toMatch(/bullet/i);
  });

  it("fresher: silent when projects and internships all have bullets", () => {
    expect(cvWarnings(validFresher())).toEqual({ experience: "", projects: "" });
  });
});

// ---- sectionTicks ----------------------------------------------------------

describe("sectionTicks", () => {
  it("ticks personal, experience for a complete experienced CV; extras until filled", () => {
    const cv = validExperienced();
    const ticks = sectionTicks(cv);
    expect(ticks.personal).toBe(true);
    expect(ticks.experience).toBe(true);
    expect(ticks.extras).toBe(false);
  });

  it("requires every skill group to have items", () => {
    const cv = validExperienced();
    cv.skills = [{ category: "Languages", items: [] }];
    expect(sectionTicks(cv).skills).toBe(false);
    cv.skills = [{ category: "Languages", items: ["Python"] }];
    expect(sectionTicks(cv).skills).toBe(true);
  });

  it("requires degree AND school for education", () => {
    const cv = validExperienced();
    cv.education = [{ degree: "B.Sc.", school: "", location: "", dates: "", details: [] }];
    expect(sectionTicks(cv).education).toBe(false);
    cv.education[0].school = "Example University";
    expect(sectionTicks(cv).education).toBe(true);
  });

  it("ticks extras when any of certifications/languages/additional_info exist", () => {
    const cv = validExperienced();
    cv.languages = ["English"];
    expect(sectionTicks(cv).extras).toBe(true);
  });

  it("fresher mode: empty experience still ticks (optional); projects drive the tick", () => {
    const cv = validFresher();
    const ticks = sectionTicks(cv);
    expect(ticks.experience).toBe(true);
    expect(ticks.projects).toBe(true);

    cv.projects[0].details = [];
    expect(sectionTicks(cv).projects).toBe(false);
  });
});
