import { getProfile } from "../data/profiles";
import { SUMMARY_EXAMPLES } from "../utils/sampleData";
import type { CVData } from "../types/cv";
import { TextAreaField } from "./ui";

interface Props {
  cv: CVData;
  update: (patch: Partial<CVData>) => void;
}

/** The field most users freeze on — coach it with an insertable example. */
export default function SummaryForm({ cv, update }: Props) {
  const fresher = getProfile(cv.profile).key === "fresher";

  return (
    <>
      <TextAreaField
        label={fresher ? "Career objective" : "Professional summary"}
        value={cv.summary}
        rows={4}
        maxLength={1200}
        hint={
          fresher
            ? "2–4 sentences: your degree, your best projects, the role you want."
            : "3–5 sentences: years of experience, core stack, what you deliver."
        }
        onChange={(summary) => update({ summary })}
      />
      <button
        type="button"
        className="insert-example"
        onClick={() => update({ summary: SUMMARY_EXAMPLES[cv.profile === "fresher" ? "fresher" : "experienced"] })}
      >
        ✨ Insert example — replace with your own details
      </button>
    </>
  );
}
