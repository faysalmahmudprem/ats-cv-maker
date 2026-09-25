/**
 * ImportCV state machine tests: idle → ready → (import | score) paths,
 * including the rule that a failed score check never blocks the import.
 * The network layer is mocked; ImportApiError stays real so the
 * instanceof-based error handling is genuinely exercised.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ImportCV from "./ImportCV";
import { ImportApiError, type ImportResult } from "../services/importApi";

vi.mock("../services/api", () => ({
  checkScore: vi.fn(),
}));
vi.mock("../services/importApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/importApi")>()),
  importCV: vi.fn(),
}));

import { checkScore } from "../services/api";
import { importCV } from "../services/importApi";

const mockedCheckScore = vi.mocked(checkScore);
const mockedImportCV = vi.mocked(importCV);

function aFile(name = "Faysal_CV.pdf"): File {
  return new File(["cv-bytes"], name, { type: "application/pdf" });
}

function parsedResult(): ImportResult {
  return {
    cv: {
      name: "Faysal",
      experience: [
        {
          title: "Dev",
          company: "Acme",
          location: "Dhaka",
          dates: "Jan 2024 - Present",
          bullets: ["Shipped the thing"],
        },
      ],
    },
    warnings: ["Could not detect a skills section."],
    meta: {
      kind: "docx",
      filename: "Faysal_CV.pdf",
      pages: 1,
      words: 300,
      sections_found: ["experience"],
    },
  };
}

function scoreResult() {
  return {
    score: 67,
    grade: "B",
    summary: "Generic backend verdict (UI shows its own line).",
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
  render(<ImportCV onImport={vi.fn()} hasExistingData={false} />);
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  await user.upload(input, file);
  return user;
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ImportCV state machine", () => {
  it("idle → ready: picking a file offers import vs score", async () => {
    await pickFile();
    expect(screen.getByText("Faysal_CV.pdf")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Import and start editing" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Check ATS readiness first →" }),
    ).toBeInTheDocument();
  });

  it("rejects files over 5 MB before any state changes", async () => {
    const user = await pickFile(
      new File([new Uint8Array(5_000_001)], "big.docx", { type: "application/msword" }),
    );
    expect(screen.getByText(/over 5 MB/i)).toBeInTheDocument();
    // Back in the error state — import/score choice never appears.
    expect(screen.queryByText("Import and start editing")).not.toBeInTheDocument();
    expect(mockedImportCV).not.toHaveBeenCalled();
    expect(user).toBeDefined();
  });

  it("ready → loading → confirm → onImport receives the parsed cv", async () => {
    const onImport = vi.fn();
    mockedImportCV.mockResolvedValue(parsedResult());
    const user = userEvent.setup();
    render(<ImportCV onImport={onImport} hasExistingData={false} />);
    await user.upload(
      document.querySelector('input[type="file"]') as HTMLInputElement,
      aFile(),
    );
    await user.click(screen.getByRole("button", { name: "Import and start editing" }));
    expect(await screen.findByRole("status")).toBeInTheDocument();
    expect(screen.getByText(/Found 1 job/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Bring it in" }));
    expect(onImport).toHaveBeenCalledTimes(1);
    expect(onImport.mock.calls[0][0]).toMatchObject({ name: "Faysal" });
  });

  it("ready → scoring → scored shows the shared score card", async () => {
    mockedCheckScore.mockResolvedValue(scoreResult());
    const user = await pickFile();
    await user.click(screen.getByRole("button", { name: "Check ATS readiness first →" }));
    expect(await screen.findByText(/ATS readiness: 67\/100/)).toBeInTheDocument();
    expect(screen.getByText("Good shape. Some quick fixes would make it stronger.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Import and fix it in CVify →" })).toBeInTheDocument();
  });

  it("score result → import runs the normal import flow", async () => {
    mockedCheckScore.mockResolvedValue(scoreResult());
    mockedImportCV.mockResolvedValue(parsedResult());
    const onImport = vi.fn();
    const user = userEvent.setup();
    render(<ImportCV onImport={onImport} hasExistingData={false} />);
    await user.upload(
      document.querySelector('input[type="file"]') as HTMLInputElement,
      aFile(),
    );
    await user.click(screen.getByRole("button", { name: "Check ATS readiness first →" }));
    await screen.findByText(/ATS readiness: 67\/100/);
    await user.click(screen.getByRole("button", { name: "Import and fix it in CVify →" }));
    expect(await screen.findByText(/Found 1 job/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Bring it in" }));
    expect(onImport).toHaveBeenCalledTimes(1);
  });

  it("score failure → score_error offers 'Import anyway' and still imports", async () => {
    mockedCheckScore.mockRejectedValue(new Error("timeout"));
    mockedImportCV.mockResolvedValue(parsedResult());
    const onImport = vi.fn();
    const user = userEvent.setup();
    render(<ImportCV onImport={onImport} hasExistingData={false} />);
    await user.upload(
      document.querySelector('input[type="file"]') as HTMLInputElement,
      aFile(),
    );
    await user.click(screen.getByRole("button", { name: "Check ATS readiness first →" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Couldn't score it — want to import anyway\?/);
    await user.click(screen.getByRole("button", { name: "Import anyway" }));
    expect(await screen.findByText(/Found 1 job/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Bring it in" }));
    expect(onImport).toHaveBeenCalledTimes(1);
  });

  it("score failure → 'Pick another file' returns to idle", async () => {
    mockedCheckScore.mockRejectedValue(new Error("timeout"));
    const user = await pickFile();
    await user.click(screen.getByRole("button", { name: "Check ATS readiness first →" }));
    await screen.findByRole("alert");
    await user.click(screen.getByRole("button", { name: "Pick another file" }));
    expect(screen.getByText("Upload .docx / .pdf")).toBeInTheDocument();
  });

  it("import API error keeps its human-readable message via ImportApiError", async () => {
    mockedImportCV.mockRejectedValue(new ImportApiError("Server hiccup (HTTP 500).", 500));
    const user = await pickFile();
    await user.click(screen.getByRole("button", { name: "Import and start editing" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Server hiccup (HTTP 500).");
  });

  it("unexpected import failures get the generic human message", async () => {
    mockedImportCV.mockRejectedValue(new TypeError("network dead"));
    const user = await pickFile();
    await user.click(screen.getByRole("button", { name: "Import and start editing" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Couldn't read that file/);
  });

  it("drag & drop also reaches the ready state", () => {
    render(<ImportCV onImport={vi.fn()} hasExistingData={false} />);
    const drop = document.querySelector(".import-drop") as HTMLElement;
    const file = aFile("Dropped_CV.docx");
    fireEvent.drop(drop, {
      dataTransfer: { files: [file] },
    });
    expect(screen.getByText("Dropped_CV.docx")).toBeInTheDocument();
  });
});
