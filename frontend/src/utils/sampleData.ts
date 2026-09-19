/**
 * Sample data used ONLY by the "Try with sample data" button.
 * Fictional example content — contains no real personal information.
 * Two variants: experienced (default) and fresher (student profile).
 */
import { emptyCV } from "../types/cv";
import type { CVData } from "../types/cv";

/** Sample text snippets users can insert into their own summary. */
export const SUMMARY_EXAMPLES: Record<string, string> = {
  experienced:
    "Software engineer with 3 years of experience building web applications and business software (ERP, POS, CRM). Comfortable across the stack: React on the front, FastAPI on the back. I ship features end-to-end and care about clean, maintainable code.",
  fresher:
    "Computer Science graduate (2025) seeking a junior software engineering role. Built 4 academic and personal projects in Python and React, including a CV generator used by my university club. Quick to learn, eager to contribute from day one.",
};

export function sampleCV(profile: "experienced" | "fresher" = "experienced"): CVData {
  if (profile === "fresher") return fresherSample();

  const cv = emptyCV();
  cv.profile = "experienced";
  cv.name = "Alex Example";
  cv.professional_title = "Software Engineer";
  cv.contact = {
    location: "Dhaka, Bangladesh",
    phone: "+880 1000-000000",
    email: "alex@example.com",
    linkedin: "linkedin.com/in/alexexample",
    github: "github.com/alexexample",
    portfolio: "alexexample.dev",
  };
  cv.summary =
    "Software engineer with experience building web applications and business software (ERP, POS, CRM).";
  cv.skills = [
    { category: "Languages", items: ["Python", "JavaScript", "PHP"] },
    { category: "Frameworks", items: ["FastAPI", "React", "Laravel"] },
  ];
  cv.experience = [
    {
      title: "Software Engineer",
      company: "Example Corp",
      location: "Dhaka",
      dates: "Jan 2024 - Present",
      bullets: [
        "Built REST APIs serving 10k daily requests.",
        "Led migration of legacy ERP modules to a modern stack.",
      ],
    },
  ];
  cv.projects = [
    {
      name: "CV Generator",
      technologies: ["Python", "python-docx"],
      description: "Generates ATS-friendly Word CVs from structured JSON.",
      details: ["Supports Unicode text, hyperlinks and bullet formatting."],
    },
  ];
  cv.education = [
    {
      degree: "B.Sc. in Computer Science",
      school: "Example University",
      location: "Dhaka",
      dates: "2019 - 2023",
      details: ["CGPA 3.80/4.00"],
    },
  ];
  cv.certifications = [
    { title: "AWS Cloud Practitioner", issuer: "Amazon", date: "2024" },
  ];
  cv.languages = ["English", "Bangla"];
  cv.additional_info = ["Open to relocation."];

  return cv;
}

/** Fresher sample: student profile, no jobs, projects as the hero. */
function fresherSample(): CVData {
  const cv = emptyCV();
  cv.profile = "fresher";
  cv.name = "Sam Example";
  cv.professional_title = "Aspiring Software Engineer";
  cv.contact = {
    location: "Dhaka, Bangladesh",
    phone: "+880 1000-000000",
    email: "sam@example.com",
    linkedin: "linkedin.com/in/samexample",
    github: "github.com/samexample",
    portfolio: "",
  };
  cv.summary =
    "Computer Science graduate seeking a junior software engineering role. Built academic and personal projects in Python and React. Quick to learn and eager to contribute from day one.";
  cv.education = [
    {
      degree: "B.Sc. in Computer Science",
      school: "Example University",
      location: "Dhaka",
      dates: "2021 - 2025",
      details: ["CGPA 3.70/4.00", "Final-year project: campus event management app."],
    },
  ];
  cv.projects = [
    {
      name: "Campus Events App",
      technologies: ["React", "FastAPI", "PostgreSQL"],
      description: "Web app for students to discover and register for campus events.",
      details: [
        "Built the registration flow used by 200+ students during club week.",
        "Designed the REST API and database schema from scratch.",
      ],
    },
    {
      name: "Expense Tracker",
      technologies: ["Python", "SQLite"],
      description: "Command-line tool that tracks monthly spending with reports.",
      details: ["Implemented CSV export and monthly summary reports."],
    },
  ];
  cv.skills = [
    { category: "Languages", items: ["Python", "JavaScript", "SQL"] },
    { category: "Tools", items: ["Git", "VS Code", "Postman"] },
  ];
  cv.experience = [
    {
      title: "Intern",
      company: "Example Software Ltd",
      location: "Dhaka",
      dates: "Jun 2024 - Aug 2024",
      bullets: ["Assisted the QA team with manual test runs and bug reports."],
    },
  ];
  cv.certifications = [
    { title: "CS50x Introduction to Computer Science", issuer: "edX", date: "2023" },
  ];
  cv.languages = ["English", "Bangla"];
  cv.additional_info = [];

  return cv;
}
