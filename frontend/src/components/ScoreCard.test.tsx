/**
 * ScoreCard presentation tests: grade → color/summary mapping, issue
 * truncation, and the 0 → score bar animation kick.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import ScoreCard from "./ScoreCard";
import type { ScoreResult } from "../services/api";

function result(overrides: Partial<ScoreResult> = {}): ScoreResult {
  return {
    score: 67,
    grade: "B",
    summary: "Backend verdict (unused by the UI).",
    categories: {},
    issues: [
      {
        severity: "high",
        title: "No achievement bullets",
        detail: "No bullets found.",
        fix: "Start bullets with action verbs",
      },
    ],
    fix_cta: true,
    ...overrides,
  };
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ScoreCard", () => {
  it("renders score, grade chip, and the human per-grade summary", () => {
    render(
      <ScoreCard score={result()} useLabel="Use it" onUse={() => {}} />,
    );
    expect(screen.getByText("ATS readiness: 67/100")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(
      screen.getByText("Good shape. Some quick fixes would make it stronger."),
    ).toBeInTheDocument();
  });

  // jsdom normalizes inline hex colors to rgb() — assert the same values.
  it.each([
    ["A", "Looks solid. A few tweaks could push it higher.", "rgb(34, 197, 94)"],
    ["B", "Good shape. Some quick fixes would make it stronger.", "rgb(34, 197, 94)"],
    ["C", "Recruiters can read it, but it needs work.", "rgb(245, 158, 11)"],
    ["D", "This CV may get filtered out. Let's fix that.", "rgb(239, 68, 68)"],
    ["F", "This CV may get filtered out. Let's fix that.", "rgb(239, 68, 68)"],
  ])("grade %s → summary + bar color", (grade, summary, color) => {
    render(
      <ScoreCard score={result({ grade, score: 85 })} useLabel="Use it" onUse={() => {}} />,
    );
    expect(screen.getByText(summary)).toBeInTheDocument();
    const fill = document.querySelector(".score-fill") as HTMLElement;
    expect(fill.style.background).toBe(color);
  });

  it("shows at most 5 issues and counts the rest", () => {
    const issues = Array.from({ length: 7 }, (_, i) => ({
      severity: "medium" as const,
      title: `Issue ${i + 1}`,
      detail: "d",
      fix: "f",
    }));
    render(
      <ScoreCard score={result({ issues })} useLabel="Use it" onUse={() => {}} />,
    );
    expect(screen.getByText("Issue 1")).toBeInTheDocument();
    expect(screen.getByText("Issue 5")).toBeInTheDocument();
    expect(screen.queryByText("Issue 6")).not.toBeInTheDocument();
    expect(screen.getByText("and 2 more issues")).toBeInTheDocument();
  });

  it("bar animates from 0 to the score after mount", async () => {
    const raf = vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
      cb(0);
      return 1;
    });
    render(
      <ScoreCard score={result({ score: 67 })} useLabel="Use it" onUse={() => {}}
      />,
    );
    await waitFor(() => {
      const fill = document.querySelector(".score-fill") as HTMLElement;
      expect(fill.style.width).toBe("67%");
    });
    raf.mockRestore();
  });
  it("primary button invokes the flow's next step", () => {
    const onUse = vi.fn();
    render(<ScoreCard score={result()} useLabel="Use it" onUse={onUse} />);
    fireEvent.click(screen.getByText("Use it"));
    expect(onUse).toHaveBeenCalledTimes(1);
  });
});
