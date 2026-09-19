/**
 * Shared inline ATS score display, used by every flow that can produce a
 * score: the import flow (score an existing CV before editing), the generate
 * flow (score the file that was just built), and the standalone score
 * checker. Pure presentation plus the bar animation — the parent owns
 * fetching and navigation.
 */
import { useEffect, useState, type CSSProperties } from "react";
import type { ScoreResult } from "../services/api";
import { Btn } from "./ui";

interface ScoreCardProps {
  score: ScoreResult;
  /** Primary next step — import the file, or jump into the editor. */
  onUse: () => void;
  useLabel: string;
  /** Optional secondary action (re-check with another file, dismiss…). */
  onSecondary?: () => void;
  secondaryLabel?: string;
}

const MAX_ISSUES = 5;

/** Human labels for the backend's category keys. */
const CATEGORY_LABELS: Record<string, string> = {
  format: "Formatting",
  contact: "Contact details",
  keywords: "Keywords",
  experience: "Experience",
  length: "Length",
  headings: "Sections",
};

const STATUS_COLOR: Record<string, string> = {
  good: "#22c55e",
  warning: "#f59e0b",
  poor: "#ef4444",
};

const SEVERITY_COLOR: Record<ScoreResult["issues"][number]["severity"], string> = {
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#22c55e",
};

/** Green for A/B, amber for C, red for D/F. */
function gradeColor(grade: string): string {
  const n = parseInt(grade, 10);
  return grade === "A" || grade === "B" || n >= 70
    ? "#22c55e"
    : grade === "C" || n >= 55
      ? "#f59e0b"
      : "#ef4444";
}

/** Our own one-liner per grade — friendlier than a generic verdict. */
function gradeSummary(grade: string): string {
  switch (grade) {
    case "A":
      return "Looks solid. A few tweaks could push it higher.";
    case "B":
      return "Good shape. Some quick fixes would make it stronger.";
    case "C":
      return "Recruiters can read it, but it needs work.";
    default:
      return "This CV may get filtered out. Let's fix that.";
  }
}

export default function ScoreCard({
  score,
  onUse,
  useLabel,
  onSecondary,
  secondaryLabel,
}: ScoreCardProps) {
  // Bar animates from 0 to the real value one frame after mount.
  const [barWidth, setBarWidth] = useState(0);
  useEffect(() => {
    const raf = requestAnimationFrame(() => setBarWidth(score.score));
    return () => cancelAnimationFrame(raf);
  }, [score]);

  const color = gradeColor(score.grade);
  const shown = score.issues.slice(0, MAX_ISSUES);
  const hidden = score.issues.length - shown.length;

  // Only categories the backend actually scored (an empty map renders none).
  const categories = Object.entries(score.categories ?? {}).filter(
    ([, c]) => c && c.max > 0,
  );

  return (
    <div
      className="score-result"
      role="status"
      style={{ "--score-color": color } as CSSProperties}
    >
      <div className="score-head">
        <div className="score-head-text">
          <span className="score-num">ATS score: {score.score}/100</span>
          <p className="score-summary">{gradeSummary(score.grade)}</p>
        </div>
        <span className="score-grade" style={{ background: color }}>
          {score.grade}
        </span>
      </div>

      <div
        className="score-bar"
        role="img"
        aria-label={`Score ${score.score} out of 100, grade ${score.grade}`}
      >
        <span
          className="score-fill"
          style={{ width: `${barWidth}%`, background: color }}
        />
      </div>

      {typeof score.word_count === "number" ? (
        <div className="score-meta">
          <span className="score-chip">
            {score.word_count.toLocaleString()} words
          </span>
        </div>
      ) : null}

      {categories.length > 0 ? (
        <div className="score-cats">
          {categories.map(([key, c]) => {
            const pct = Math.max(0, Math.min(100, Math.round((c.score / c.max) * 100)));
            return (
              <div className="score-cat" key={key}>
                <span className="score-cat-name">{CATEGORY_LABELS[key] ?? key}</span>
                <span className="score-cat-val">
                  {c.score}/{c.max}
                </span>
                <span className="score-cat-track">
                  <span
                    className="score-cat-fill"
                    style={{ width: `${pct}%`, background: STATUS_COLOR[c.status] ?? "#94a3b8" }}
                  />
                </span>
              </div>
            );
          })}
        </div>
      ) : null}

      {shown.length > 0 ? (
        <div className="score-issues">
          <span className="inline-label">What&apos;s holding it back</span>
          <ul>
            {shown.map((issue, i) => (
              <li className={`score-issue sev-${issue.severity}`} key={i}>
                <span
                  className="score-issue-dot"
                  style={{ background: SEVERITY_COLOR[issue.severity] }}
                  aria-hidden="true"
                />
                <span className="score-issue-body">
                  <strong>{issue.title}</strong>
                  <span className="score-fix">{issue.fix}</span>
                </span>
              </li>
            ))}
          </ul>
          {hidden > 0 ? <p className="import-note">and {hidden} more issues</p> : null}
        </div>
      ) : null}

      <div className="score-actions">
        <Btn variant="primary" onClick={onUse}>
          {useLabel}
        </Btn>
        {onSecondary && secondaryLabel ? (
          <Btn variant="ghost" onClick={onSecondary}>
            {secondaryLabel}
          </Btn>
        ) : null}
      </div>
    </div>
  );
}
