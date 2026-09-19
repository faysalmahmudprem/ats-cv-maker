/**
 * Score-only entry point: check any existing DOCX/PDF for ATS readiness
 * without importing it into the editor.
 *
 * Deliberately independent of the import and generate flows — this flow
 * never reads or writes editor state, so scoring a file can't clobber a
 * CV the user is already building. It shares the `checkScore` client and
 * the `ScoreCard` presentation with those flows.
 *
 * Flow: idle → file picked → scoring → scored (ScoreCard inline)
 *         scoring fails → error → try again, or pick another file
 */
import { useRef, useState } from "react";
import { checkScore, type ScoreResult } from "../services/api";
import { SECTION_IDS, scrollToSection } from "./SectionNav";
import ScoreCard from "./ScoreCard";
import { Btn } from "./ui";

type Phase = "idle" | "scoring" | "scored" | "error";

export default function ScoreChecker() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [score, setScore] = useState<ScoreResult | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function pickFile(picked: File | undefined) {
    if (!picked) return;
    if (picked.size > 5_000_000) {
      setPhase("error");
      setErrorMessage("That file is over 5 MB. Try exporting a smaller version.");
      return;
    }
    setFile(picked);
    setScore(null);
    setErrorMessage("");
    // One action here, so score immediately rather than asking again.
    void runScore(picked);
  }

  async function runScore(target?: File) {
    const chosen = target ?? file;
    if (!chosen) return;
    setPhase("scoring");
    setErrorMessage("");
    try {
      setScore(await checkScore(chosen));
      setPhase("scored");
    } catch {
      setPhase("error");
      setErrorMessage(
        "Couldn't score that file. It may be corrupted, or the service is offline.",
      );
    }
  }

  function reset() {
    setPhase("idle");
    setFile(null);
    setScore(null);
    setErrorMessage("");
  }

  // ---------------------------------------------------------------------
  // Score result (shared ScoreCard). "Build your CV" only navigates —
  // it never touches editor state.
  // ---------------------------------------------------------------------

  if (phase === "scored" && score) {
    return (
      <ScoreCard
        score={score}
        useLabel="Build your CV with these fixes →"
        onUse={() => scrollToSection(SECTION_IDS.personal)}
        secondaryLabel="Check another CV"
        onSecondary={reset}
      />
    );
  }

  // ---------------------------------------------------------------------
  // Error (unreadable file or service offline)
  // ---------------------------------------------------------------------

  if (phase === "error") {
    return (
      <div className="import-error" role="alert">
        <span>{errorMessage}</span>
        <span className="import-actions">
          <Btn variant="soft" onClick={() => void runScore()} disabled={!file}>
            Try again
          </Btn>
          <Btn variant="ghost" onClick={reset}>
            Pick another file
          </Btn>
        </span>
      </div>
    );
  }

  // ---------------------------------------------------------------------
  // Dropzone (idle, or scoring in flight)
  // ---------------------------------------------------------------------

  const scoring = phase === "scoring";
  return (
    <>
      <div
        className={`score-drop ${dragOver ? "over" : ""} ${scoring ? "busy" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          pickFile(e.dataTransfer.files?.[0]);
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".docx,.pdf"
          className="visually-hidden-input"
          aria-label="Upload a CV to score (DOCX or PDF)"
          onChange={(e) => {
            pickFile(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
        <span className="score-drop-icon" aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            width="24"
            height="24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <path d="M14 2v6h6" />
            <path d="M9 15l2 2 4-4" />
          </svg>
        </span>
        <div className="score-drop-copy">
          <strong>Score a CV you already have</strong>
          <span>
            Upload a .docx or .pdf and see how recruiting software reads it.
            Nothing is saved, and your editor stays untouched.
          </span>
        </div>
        <Btn
          variant="primary"
          onClick={() => inputRef.current?.click()}
          loading={scoring}
          disabled={scoring}
        >
          <span className="btn-label">
            {scoring ? "Scoring…" : "Upload .docx / .pdf"}
          </span>
        </Btn>
        <span className="score-drop-hint">
          PDF or Word · up to 5 MB · click to browse or drop a file
        </span>
      </div>
      {scoring ? (
        <span className="score-scanning" role="status">
          Scoring your CV…
        </span>
      ) : null}
    </>
  );
}
