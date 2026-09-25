/**
 * ScoreChecker state machine tests: idle → pick file → auto-score → scored
 * (shared ScoreCard), plus the failure path and the 5 MB guard. The network
 * layer and the scroll helper are mocked; the component itself must never
 * receive an editor-state setter (score-only, no side effects).
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ScoreChecker from "./ScoreChecker";

vi.mock("../services/api", () => ({ checkScore: vi.fn() }));
vi.mock("./SectionNav", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./SectionNav")>()),
  scrollToSection: vi.fn(),
}));

import { checkScore } from "../services/api";
import { SECTION_IDS, scrollToSection } from "./SectionNav";

const mockedCheckScore = vi.mocked(checkScore);
const mockedScroll = vi.mocked(scrollToSection);

function aFile(name = "Existing_CV.pdf"): File {
  return new File(["cv-bytes"], name, { type: "application/pdf" });
}

function scoreResult() {
  return {
    score: 67,
    grade: "B",
    summary: "Backend verdict (UI shows its own line).",
    categories: {},
    issues: [
      {
        severity: "medium" as const,
        title: "LinkedIn URL missing",
        detail: "No linkedin.com anywhere.",
        fix: "Add linkedin.com/in/yourname to contacts",
      },
    ],
    fix_cta: true,
  };
}

async function pickFile(file = aFile()) {
  const user = userEvent.setup();
  render(<ScoreChecker />);
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  await user.upload(input, file);
  return user;
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ScoreChecker", () => {
  it("idle: shows the score-only dropzone and upload button", () => {
    render(<ScoreChecker />);
    expect(screen.getByText("Score a CV you already have")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload .docx / .pdf" })).toBeInTheDocument();
  });

  it("job-match field: label is associated and stacked above a full-width textarea", () => {
    render(<ScoreChecker />);
    const label = screen.getByText(
      "Paste a job description for a job-match score (optional)",
    );
    expect(label.tagName).toBe("LABEL");
    const ta = screen.getByPlaceholderText(/Paste the job posting here/);
    expect(ta.tagName).toBe("TEXTAREA");
    expect(label.getAttribute("for")).toBe(ta.id);
    // Structural guard against the squeezed-column regression: the pair
    // must live in a block-level field wrapper, not as bare inline siblings.
    expect(ta.closest(".score-jd-field")).not.toBeNull();
    expect(label.closest(".score-jd-field")).toBe(ta.closest(".score-jd-field"));
  });

  it("picking a file scores it immediately and shows the shared ScoreCard", async () => {
    mockedCheckScore.mockResolvedValue(scoreResult());
    await pickFile();
    expect(await screen.findByText(/ATS readiness: 67\/100/)).toBeInTheDocument();
    expect(mockedCheckScore).toHaveBeenCalledTimes(1);
    expect(mockedCheckScore.mock.calls[0][0]).toBeInstanceOf(File);
    expect(
      screen.getByRole("button", { name: "Build your CV with these fixes →" }),
    ).toBeInTheDocument();
  });

  it("'Build your CV' only scrolls to the editor — never a state side effect", async () => {
    mockedCheckScore.mockResolvedValue(scoreResult());
    const user = await pickFile();
    await screen.findByText(/ATS readiness: 67\/100/);
    await user.click(screen.getByRole("button", { name: "Build your CV with these fixes →" }));
    expect(mockedScroll).toHaveBeenCalledWith(SECTION_IDS.personal);
  });

  it("'Check another CV' returns to the idle dropzone", async () => {
    mockedCheckScore.mockResolvedValue(scoreResult());
    const user = await pickFile();
    await screen.findByText(/ATS readiness: 67\/100/);
    await user.click(screen.getByRole("button", { name: "Check another CV" }));
    expect(screen.getByText("Score a CV you already have")).toBeInTheDocument();
  });

  it("rejects files over 5 MB without calling the scorer", async () => {
    await pickFile(new File([new Uint8Array(5_000_001)], "big.pdf", { type: "application/pdf" }));
    expect(screen.getByText(/over 5 MB/i)).toBeInTheDocument();
    expect(mockedCheckScore).not.toHaveBeenCalled();
  });

  it("score failure shows a retry alert, and 'Pick another file' returns to idle", async () => {
    mockedCheckScore.mockRejectedValue(new Error("timeout"));
    const user = await pickFile();
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Couldn't score that file/);
    await user.click(screen.getByRole("button", { name: "Pick another file" }));
    expect(screen.getByText("Score a CV you already have")).toBeInTheDocument();
  });
});
