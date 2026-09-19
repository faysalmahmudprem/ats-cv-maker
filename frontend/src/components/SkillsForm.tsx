import type { CVData, SkillGroup } from "../types/cv";
import { Btn, EntryCard, EmptyState, TagInput } from "./ui";

interface Props {
  cv: CVData;
  update: (patch: Partial<CVData>) => void;
}

const PRESET_CATEGORIES = ["Languages", "Frameworks", "Tools", "Databases", "Soft Skills"];

/**
 * Multiple skill groups (Languages / Frameworks / Tools / ...).
 * The backend already accepts up to 25 groups; each renders as its own
 * "Category: a, b, c" line in both DOCX and PDF.
 */
export default function SkillsForm({ cv, update }: Props) {
  const groups = cv.skills;

  function setGroups(next: SkillGroup[]) {
    update({ skills: next });
  }

  function patchAt(index: number, patch: Partial<SkillGroup>) {
    setGroups(groups.map((g, i) => (i === index ? { ...g, ...patch } : g)));
  }

  function move(index: number, delta: number) {
    const to = index + delta;
    if (to < 0 || to >= groups.length) return;
    const next = [...groups];
    [next[index], next[to]] = [next[to], next[index]];
    setGroups(next);
  }

  const suggestCategory = () => {
    const used = new Set(groups.map((g) => g.category));
    return PRESET_CATEGORIES.find((c) => !used.has(c)) ?? "";
  };

  return (
    <>
      {groups.length === 0 ? (
        <EmptyState
          text="No skills added yet."
          action={
            <Btn
              variant="soft"
              onClick={() => setGroups([{ category: "Languages", items: [] }])}
            >
              + Add skill group
            </Btn>
          }
        />
      ) : (
        groups.map((group, i) => (
          <EntryCard
            key={i}
            title={group.category || `Group ${i + 1}`}
            first={i === 0}
            last={i === groups.length - 1}
            onMoveUp={() => move(i, -1)}
            onMoveDown={() => move(i, 1)}
            onRemove={() => setGroups(groups.filter((_, j) => j !== i))}
          >
            <TagInput
              tags={group.items}
              onChange={(items) => patchAt(i, { items })}
              placeholder="e.g. Python — then press Enter"
              maxTags={40}
            />
            <GroupCategory
              value={group.category}
              onChange={(category) => patchAt(i, { category })}
            />
          </EntryCard>
        ))
      )}
      {groups.length > 0 ? (
        <div className="add-row">
          <Btn variant="soft" onClick={() => setGroups([...groups, { category: suggestCategory(), items: [] }])}>
            + Add skill group
          </Btn>
        </div>
      ) : null}
      <p className="field-hint">
        Grouping skills (e.g. Languages, Tools) reads better than one long
        list — each group becomes its own line on the CV.
      </p>
    </>
  );
}

/** Category label with quick-pick buttons for common names. */
function GroupCategory({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="field-wrap">
      <div className="category-row">
        <input
          type="text"
          className="category-input"
          value={value}
          maxLength={60}
          placeholder="Group label (e.g. Languages)"
          aria-label="Skill group label"
          onChange={(e) => onChange(e.target.value)}
        />
        <span className="category-presets">
          {PRESET_CATEGORIES.filter((c) => c !== value)
            .slice(0, 3)
            .map((c) => (
              <button
                key={c}
                type="button"
                className="chip-btn"
                onClick={() => onChange(c)}
              >
                {c}
              </button>
            ))}
        </span>
      </div>
    </div>
  );
}
