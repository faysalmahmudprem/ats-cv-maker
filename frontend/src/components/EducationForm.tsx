import type { CVData, Education } from "../types/cv";
import { emptyEducation } from "../types/cv";
import { BulletsInput, Btn, EntryCard, EmptyState, Field } from "./ui";

interface Props {
  cv: CVData;
  update: (patch: Partial<CVData>) => void;
}

export default function EducationForm({ cv, update }: Props) {
  const list = cv.education;

  function setList(next: Education[]) {
    update({ education: next });
  }

  function patchAt(index: number, patch: Partial<Education>) {
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
          text="No education added yet."
          action={
            <Btn variant="soft" onClick={() => setList([emptyEducation()])}>
              + Add education
            </Btn>
          }
        />
      ) : (
        list.map((edu, i) => (
          <EntryCard
            key={i}
            title={edu.degree || edu.school || `Education ${i + 1}`}
            first={i === 0}
            last={i === list.length - 1}
            onMoveUp={() => move(i, -1)}
            onMoveDown={() => move(i, 1)}
            onRemove={() => setList(list.filter((_, j) => j !== i))}
          >
            <div className="grid-2">
              <Field
                label="Degree"
                value={edu.degree}
                maxLength={100}
                onChange={(degree) => patchAt(i, { degree })}
              />
              <Field
                label="School / University"
                value={edu.school}
                maxLength={100}
                onChange={(school) => patchAt(i, { school })}
              />
            </div>
            <div className="grid-2">
              <Field
                label="Location"
                value={edu.location}
                maxLength={80}
                onChange={(location) => patchAt(i, { location })}
              />
              <Field
                label="Dates"
                value={edu.dates}
                maxLength={60}
                onChange={(dates) => patchAt(i, { dates })}
              />
            </div>
            <BulletsInput
              label="Details (optional)"
              bullets={edu.details}
              onChange={(details) => patchAt(i, { details })}
            />
          </EntryCard>
        ))
      )}
    </>
  );
}
