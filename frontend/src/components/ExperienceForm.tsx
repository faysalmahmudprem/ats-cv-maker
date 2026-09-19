import { getProfile } from "../data/profiles";
import type { CVData, Experience } from "../types/cv";
import { emptyExperience } from "../types/cv";
import type { CVWarnings } from "../utils/validate";
import { BulletsInput, Btn, EntryCard, EmptyState, Field } from "./ui";

interface Props {
  cv: CVData;
  warnings: CVWarnings;
  update: (patch: Partial<CVData>) => void;
}

export default function ExperienceForm({ cv, warnings, update }: Props) {
  const list = cv.experience;
  const fresher = getProfile(cv.profile).key === "fresher";

  function setList(next: Experience[]) {
    update({ experience: next });
  }

  function patchAt(index: number, patch: Partial<Experience>) {
    setList(list.map((e, i) => (i === index ? { ...e, ...patch } : e)));
  }

  function move(index: number, delta: number) {
    const to = index + delta;
    if (to < 0 || to >= list.length) return;
    const next = [...list];
    [next[index], next[to]] = [next[to], next[index]];
    setList(next);
  }

  return (
    <>
      {list.length === 0 ? (
        <EmptyState
          text={
            fresher
              ? "No internships or part-time work — that's fine, this section is optional for freshers."
              : "No work experience added yet."
          }
          action={
            <Btn variant="soft" onClick={() => setList([emptyExperience()])}>
              {fresher ? "+ Add internship" : "+ Add job"}
            </Btn>
          }
        />
      ) : (
        list.map((job, i) => (
          <EntryCard
            key={i}
            title={job.title || job.company || `Job ${i + 1}`}
            first={i === 0}
            last={i === list.length - 1}
            onMoveUp={() => move(i, -1)}
            onMoveDown={() => move(i, 1)}
            onRemove={() => setList(list.filter((_, j) => j !== i))}
          >
            <div className="grid-2">
              <Field
                label="Job title"
                value={job.title}
                maxLength={80}
                onChange={(title) => patchAt(i, { title })}
              />
              <Field
                label="Company"
                value={job.company}
                maxLength={80}
                onChange={(company) => patchAt(i, { company })}
              />
            </div>
            <div className="grid-2">
              <Field
                label="Location"
                value={job.location}
                maxLength={80}
                onChange={(location) => patchAt(i, { location })}
              />
              <Field
                label="Dates (e.g. Jan 2024 - Present)"
                value={job.dates}
                maxLength={60}
                onChange={(dates) => patchAt(i, { dates })}
              />
            </div>
            <BulletsInput
              label={fresher ? "What you did" : "Achievements"}
              bullets={job.bullets}
              onChange={(bullets) => patchAt(i, { bullets })}
              placeholder="e.g. Built REST APIs serving 10k daily requests"
            />
            {/* Advisory, not blocking: bulletless entries still download. */}
            {warnings.experience && job.bullets.length === 0 ? (
              <p className="field-warn" role="status">
                {warnings.experience}
              </p>
            ) : null}
          </EntryCard>
        ))
      )}
    </>
  );
}
