/**
 * Import CV: upload an existing DOCX/PDF, then either pull it into the
 * editor or check how it scores with ATS software first — inline, no
 * modal, no extra page. The score is a side quest: a failing score check
 * never blocks the import.
 *
 * Flow (state machine):
 *   idle → file picked → "ready"
 *     → "Import and start editing"  → loading → confirm → onImport()
 *     → "Check ATS score first"     → scoring → scored (result inline)
 *         → "Import and fix it in CVify" → existing import flow
 *         → "Check a different file"     → back to idle
 *     score check fails → score_error → import anyway, or pick another file
 */
import { useRef, useState } from "react";
import { checkScore } from "../services/api";
import { ImportApiError, importCV, type ImportResult } from "../services/importApi";
import ScoreCard from "./ScoreCard";
import { Btn } from "./ui";

interface Props {
  /** Receives the parsed CV data; caller decides merge vs replace. */
  onImport: (cv: Partial<ImportResult["cv"]>) => void;
  /** True when the current editor has content the user might overwrite. */
  hasExistingData: boolean;
}

type Phase =
  | "idle"
  | "ready" // file picked, waiting for a choice
  | "loading" // parsing for import
  | "confirm" // parsed, showing what we found
  | "error" // import parsing failed
  | "scoring" // score check in flight
  | "scored" // score result on screen
  | "score_error"; // score check failed (import still available)

export default function ImportCV({ onImport, hasExistingData }: Props) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [score, setScore] = useState<Awaited<ReturnType<typeof checkScore>> | null>(null);
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
    setResult(null);
    setScore(null);
    setErrorMessage("");
    setPhase("ready");
  }

  async function runImport() {
    if (!file) return;
    setPhase("loading");
    setErrorMessage("");
    try {
      const parsed = await importCV(file);
      setResult(parsed);
      setPhase("confirm");
    } catch (err) {
      setPhase("error");
      setErrorMessage(
        err instanceof ImportApiError
          ? err.message
          : "Couldn't read that file — try again, or pick a different one.",
      );
    }
  }

  async function runScore() {
    if (!file) return;
    setPhase("scoring");
    setErrorMessage("");
    try {
      setScore(await checkScore(file));
      setPhase("scored");
    } catch {
      setPhase("score_error");
      setErrorMessage("Couldn't score it — want to import anyway?");
    }
  }

  function confirmImport() {
    if (result) onImport(result.cv);
    reset();
  }

  function reset() {
    setPhase("idle");
    setFile(null);
    setResult(null);
    setScore(null);
    setErrorMessage("");
  }

  // ---------------------------------------------------------------------
  // Dropzone + file-ready options
  // ---------------------------------------------------------------------

  if (phase === "idle" || phase === "loading" || phase === "scoring") {
    return (
      <div className="import-cv">
        <div
          className={`import-drop ${dragOver ? "over" : ""}`}
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
            aria-label="Upload your existing CV (DOCX or PDF)"
            onChange={(e) => {
              pickFile(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
          <div className="import-copy">
            <strong>Already have a CV?</strong>
            <span>
              Upload it and pick what to do: pull it into the editor, or see
              how it scores with recruiting software first. Nothing gets saved.
            </span>
          </div>
          <Btn
            variant="soft"
            onClick={() => inputRef.current?.click()}
            loading={phase !== "idle"}
            disabled={phase !== "idle"}
          >
            <span className="btn-label">
              {phase === "loading" || phase === "scoring"
                ? "Reading your CV…"
                : "Upload .docx / .pdf"}
            </span>
          </Btn>
        </div>
        {phase !== "idle" ? (
          <p className="import-note" role="status">
            Reading your CV…
          </p>
        ) : null}
      </div>
    );
  }

  // ---------------------------------------------------------------------
  // File picked: choose import vs score
  // ---------------------------------------------------------------------

  if (phase === "ready" && file) {
    return (
      <div className="import-cv">
        <div className="import-filecard" role="status">
          <span className="import-fileicon" aria-hidden="true">
            📄
          </span>
          <span className="import-filename">{file.name}</span>
        </div>
        <div className="import-choose">
          <Btn variant="primary" onClick={runImport}>
            Import and start editing
          </Btn>
          <div className="import-or" aria-hidden="true">
            <span>or</span>
          </div>
          <div className="import-scorepitch">
            <Btn variant="soft" onClick={runScore}>
              Check ATS score first →
            </Btn>
            <span className="import-pitch">
              See what recruiting software thinks of your CV before you edit.
            </span>
          </div>
        </div>
        <button type="button" className="link-btn" onClick={reset}>
          Pick a different file
        </button>
      </div>
    );
  }

  // ---------------------------------------------------------------------
  // Score result (inline, shared ScoreCard)
  // ---------------------------------------------------------------------

  if (phase === "scored" && score) {
    return (
      <div className="import-cv">
        <ScoreCard
          score={score}
          useLabel="Import and fix it in CVify →"
          onUse={runImport}
          secondaryLabel="Check a different file"
          onSecondary={reset}
        />
      </div>
    );
  }

  // ---------------------------------------------------------------------
  // Import confirm (parsed, waiting for go-ahead)
  // ---------------------------------------------------------------------

  if (phase === "confirm" && result) {
    return (
      <div className="import-cv">
        <div className="import-confirm" role="status">
          <strong>
            Found{" "}
            {result.cv.experience?.length
              ? `${result.cv.experience.length} job${result.cv.experience.length === 1 ? "" : "s"}`
              : "no jobs"}
            {result.cv.education?.length
              ? `, ${result.cv.education.length} education ${result.cv.education.length === 1 ? "entry" : "entries"}`
              : ""}
            . Give it a once-over after it loads.
          </strong>
          {result.warnings.length > 0 ? (
            <ul className="import-warnings">
              {result.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          ) : null}
          <div className="import-actions">
            <Btn variant="primary" onClick={confirmImport}>
              {hasExistingData ? "Replace what I've written" : "Bring it in"}
            </Btn>
            <Btn variant="ghost" onClick={reset}>
              Cancel
            </Btn>
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------
  // Errors (import failed, or score failed — import still on the table)
  // ---------------------------------------------------------------------

  const scoreFailed = phase === "score_error";
  return (
    <div className="import-cv">
      <div className="import-error" role="alert">
        <span>{errorMessage}</span>
        <span className="import-actions">
          <Btn variant="soft" onClick={runImport} disabled={!file}>
            {scoreFailed ? "Import anyway" : "Try again"}
          </Btn>
          <Btn variant="ghost" onClick={reset}>
            Pick another file
          </Btn>
        </span>
      </div>
    </div>
  );
}
