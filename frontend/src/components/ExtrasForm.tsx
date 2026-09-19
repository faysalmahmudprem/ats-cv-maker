import type { CVData } from "../types/cv";
import { emptyCertification } from "../types/cv";
import { BulletsInput, Btn, EntryCard, EmptyState, Field, TagInput } from "./ui";

interface Props {
  cv: CVData;
  update: (patch: Partial<CVData>) => void;
}

export default function ExtrasForm({ cv, update }: Props) {
  const certs = cv.certifications;

  function setCerts(next: CVData["certifications"]) {
    update({ certifications: next });
  }

  function patchCert(index: number, patch: Partial<CVData["certifications"][number]>) {
    setCerts(certs.map((cert, i) => (i === index ? { ...cert, ...patch } : cert)));
  }

  return (
    <>
      <div className="subhead">Certifications</div>
      {certs.length === 0 ? (
        <EmptyState
          text="No certifications added yet."
          action={
            <Btn variant="soft" onClick={() => setCerts([emptyCertification()])}>
              + Add certification
            </Btn>
          }
        />
      ) : (
        certs.map((cert, i) => (
          <EntryCard
            key={i}
            title={cert.title || `Certification ${i + 1}`}
            first={i === 0}
            last={i === certs.length - 1}
            onMoveUp={() =>
              setCerts(
                certs.map((c, j) => (j === i - 1 ? certs[i] : j === i ? certs[i - 1] : c)),
              )
            }
            onMoveDown={() =>
              setCerts(
                certs.map((c, j) => (j === i + 1 ? certs[i] : j === i ? certs[i + 1] : c)),
              )
            }
            onRemove={() => setCerts(certs.filter((_, j) => j !== i))}
          >
            <div className="grid-2">
              <Field
                label="Title"
                value={cert.title}
                maxLength={120}
                onChange={(title) => patchCert(i, { title })}
              />
              <Field
                label="Issuer"
                value={cert.issuer}
                maxLength={80}
                onChange={(issuer) => patchCert(i, { issuer })}
              />
            </div>
            <Field
              label="Date (e.g. 2024)"
              value={cert.date}
              maxLength={40}
              onChange={(date) => patchCert(i, { date })}
            />
          </EntryCard>
        ))
      )}

      <div className="subhead">Languages</div>
      <TagInput
        tags={cv.languages}
        onChange={(languages) => update({ languages })}
        placeholder="e.g. English — press Enter"
        maxTags={10}
      />

      <div className="subhead">Additional information</div>
      <BulletsInput
        label="Extra lines (optional)"
        bullets={cv.additional_info}
        onChange={(additional_info) => update({ additional_info })}
        placeholder="One line per bullet, e.g. “Open to relocation.”"
      />
    </>
  );
}
