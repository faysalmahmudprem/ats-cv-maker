import type { CVData, Project } from "../types/cv";
import { emptyProject } from "../types/cv";
import { BulletsInput, Btn, EntryCard, EmptyState, Field, TagInput, TextAreaField } from "./ui";

interface Props {
  cv: CVData;
  update: (patch: Partial<CVData>) => void;
}

export default function ProjectsForm({ cv, update }: Props) {
  const list = cv.projects;

  function setList(next: Project[]) {
    update({ projects: next });
  }

  function patchAt(index: number, patch: Partial<Project>) {
    setList(list.map((p, i) => (i === index ? { ...p, ...patch } : p)));
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
          text="No projects added yet."
          action={
            <Btn variant="soft" onClick={() => setList([emptyProject()])}>
              + Add project
            </Btn>
          }
        />
      ) : (
        list.map((project, i) => (
          <EntryCard
            key={i}
            title={project.name || `Project ${i + 1}`}
            first={i === 0}
            last={i === list.length - 1}
            onMoveUp={() => move(i, -1)}
            onMoveDown={() => move(i, 1)}
            onRemove={() => setList(list.filter((_, j) => j !== i))}
          >
            <Field
              label="Project name"
              value={project.name}
              maxLength={80}
              onChange={(name) => patchAt(i, { name })}
            />
            <div className="field-wrap">
              <span className="inline-label">Technologies</span>
              <TagInput
                tags={project.technologies}
                onChange={(technologies) => patchAt(i, { technologies })}
                placeholder="e.g. React — press Enter"
                maxTags={20}
              />
            </div>
            <TextAreaField
              label="Short description (optional)"
              value={project.description}
              rows={2}
              maxLength={600}
              onChange={(description) => patchAt(i, { description })}
            />
            <BulletsInput
              label="Details"
              bullets={project.details}
              onChange={(details) => patchAt(i, { details })}
              placeholder="e.g. Built the registration flow used by 200+ students"
            />
          </EntryCard>
        ))
      )}
    </>
  );
}
