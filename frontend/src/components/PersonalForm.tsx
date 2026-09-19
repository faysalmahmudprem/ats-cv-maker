import type { CVData } from "../types/cv";
import type { CVProblems } from "../utils/validate";
import { Field } from "./ui";

interface Props {
  cv: CVData;
  problems: CVProblems;
  update: (patch: Partial<CVData>) => void;
}

export default function PersonalForm({ cv, problems, update }: Props) {
  const c = cv.contact;

  function setContact(patch: Partial<CVData["contact"]>) {
    update({ contact: { ...c, ...patch } });
  }

  return (
    <>
      <div className="grid-2">
        <Field
          label="Full name"
          value={cv.name}
          maxLength={80}
          required
          autoComplete="name"
          error={problems.name}
          onChange={(name) => update({ name })}
        />
        <Field
          label="Job title"
          value={cv.professional_title}
          maxLength={80}
          required
          error={problems.professional_title}
          onChange={(professional_title) => update({ professional_title })}
        />
      </div>
      <div className="grid-2">
        <Field
          label="Email"
          type="email"
          value={c.email}
          maxLength={120}
          required
          autoComplete="email"
          inputMode="email"
          error={problems.email}
          onChange={(email) => setContact({ email })}
        />
        <Field
          label="Phone"
          type="tel"
          value={c.phone}
          maxLength={40}
          required
          autoComplete="tel"
          inputMode="tel"
          error={problems.phone}
          onChange={(phone) => setContact({ phone })}
        />
      </div>
      <div className="grid-2">
        <Field
          label="Location (City, Country)"
          value={c.location}
          maxLength={80}
          onChange={(location) => setContact({ location })}
        />
        <Field
          label="LinkedIn"
          value={c.linkedin}
          maxLength={120}
          inputMode="url"
          onChange={(linkedin) => setContact({ linkedin })}
        />
      </div>
      <div className="grid-2">
        <Field
          label="GitHub"
          value={c.github}
          maxLength={120}
          inputMode="url"
          onChange={(github) => setContact({ github })}
        />
        <Field
          label="Portfolio"
          value={c.portfolio}
          maxLength={120}
          inputMode="url"
          onChange={(portfolio) => setContact({ portfolio })}
        />
      </div>
    </>
  );
}
