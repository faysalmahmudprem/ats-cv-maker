/**
 * API service: the ONLY place that talks to the FastAPI backend.
 *
 * The backend URL is never hard-coded. It comes from the VITE_API_URL
 * environment variable (see .env.example). During development Vite can
 * also proxy /api so the frontend works with zero configuration.
 */
import type { CVData } from "../types/cv";
import { filenameFromDisposition } from "../utils/download";

export const API_BASE: string = import.meta.env.VITE_API_URL ?? "";

export const DOCX_MIME =
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
export const PDF_MIME = "application/pdf";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

/**
 * Real backend health probe used by the header status indicator.
 * Unlike navigator.onLine, this actually answers "can we reach the API?".
 *
 * Strictness matters: if VITE_API_URL is missing in production, the fetch
 * hits the frontend host's SPA fallback, which returns 200 + index.html.
 * Checking res.ok alone would show "API ready" while every download is
 * broken — so the response must also be the API's actual JSON shape.
 */
export async function checkBackendHealth(): Promise<boolean> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5_000);
  try {
    const res = await fetch(`${API_BASE}/api/health`, {
      signal: controller.signal,
    });
    if (!res.ok) return false;
    const data = (await res.json()) as { status?: string };
    return data.status === "ok";
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

export interface ScoreResult {
  score: number;
  grade: string;
  summary: string;
  categories: Record<
    string,
    { score: number; max: number; status: string }
  >;
  issues: Array<{
    severity: "high" | "medium" | "low";
    title: string;
    detail: string;
    fix: string;
  }>;
  fix_cta: boolean;
  /** Word count of the scored document (returned by the backend). */
  word_count?: number;
  /** Optional job-description match supplement (backend only when JD sent). */
  jd_match?: {
    score: number;
    matched: string[];
    missing: string[];
    jd_keywords: number;
  };
}

/**
 * Ask the backend how an existing CV scores with ATS software.
 * Accepts a user-picked File (import flow) or a freshly generated Blob
 * (generate flow) — a Blob has no name, so one is supplied; the backend
 * decides the extractor from the filename extension. 15s ceiling — a
 * score check is optional, never worth a long wait.
 */
export async function checkScore(
  file: Blob,
  options: { filename?: string; jobDescription?: string } = {},
): Promise<ScoreResult> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15_000);
  const form = new FormData();
  const name =
    options.filename ?? (file instanceof File && file.name ? file.name : "CV.docx");
  form.append("file", file, name);
  if (options.jobDescription?.trim()) {
    form.append("job_description", options.jobDescription.trim().slice(0, 20000));
  }

  try {
    const res = await fetch(`${API_BASE}/api/score-cv`, {
      method: "POST",
      body: form,
      signal: controller.signal,
    });
    if (!res.ok) {
      let message = "Score check failed";
      try {
        const data = await res.json();
        if (typeof (data as { error?: unknown }).error === "string") {
          message = (data as { error: string }).error;
        } else if (typeof (data as { detail?: unknown }).detail === "string") {
          message = (data as { detail: string }).detail;
        } else {
          message = `Score check failed (HTTP ${res.status})`;
        }
      } catch {
        message = `Score check failed (HTTP ${res.status})`;
      }
      throw new Error(message);
    }
    return (await res.json()) as ScoreResult;
  } finally {
    clearTimeout(timer);
  }
}

interface GenerateResult {
  blob: Blob;
  filename: string;
}

/**
 * POST the CV data and return the generated document (DOCX or PDF) as a
 * Blob plus the filename chosen by the backend (falls back to a
 * client-side name).
 */
export async function generateCV(cv: CVData, format: "docx" | "pdf" = "docx"): Promise<GenerateResult> {
  // Hard timeout so a hung backend can never spin the button forever.
  // Free hosting cold starts can take ~30s, so 60s is a generous ceiling.
  const GENERATE_TIMEOUT_MS = 60_000;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), GENERATE_TIMEOUT_MS);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/generate-cv`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...cv, format }),
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(
        "Gave up after 60 seconds — the server's having a moment. Try again?",
        0,
      );
    }
    // fetch only throws on network-level failures
    throw new ApiError(
      `Can't reach the server${API_BASE ? ` (${API_BASE})` : ""}. Check your connection and try again.`,
      0,
    );
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    // Backend errors are JSON: {"detail": [...|"message"]} or {"error": "..."}
    let message = `Server error (HTTP ${res.status}).`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") {
        message = data.detail;
      } else if (Array.isArray(data.detail) && data.detail.length > 0) {
        const first = data.detail[0];
        const field = (first.loc ?? []).slice(1).join(".");
        message = field
          ? `${field.replace(/\./g, " ")}: ${first.msg}`
          : String(first.msg ?? message);
      } else if (typeof data.error === "string") {
        message = data.error;
      }
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(message, res.status);
  }

  // Guard against a misconfigured deployment: without VITE_API_URL the
  // request can land on the frontend host's SPA fallback, which answers
  // 200 + index.html. res.ok alone would save an HTML page named
  // "Something_CV.docx" — so the Content-Type must be the real document.
  const expectedMime = format === "pdf" ? PDF_MIME : DOCX_MIME;
  const contentType = (res.headers.get("Content-Type") ?? "").toLowerCase();
  if (!contentType.includes(expectedMime)) {
    throw new ApiError(
      "The server is misconfigured and did not return a CV file. " +
        "Please try again later or report this issue.",
      res.status,
    );
  }

  const blob = await res.blob();
  if (blob.size === 0) {
    throw new ApiError("The server returned an empty file.", res.status);
  }

  const backendName = filenameFromDisposition(res.headers.get("Content-Disposition"));
  const fallback = `${cv.name.trim().replace(/[^A-Za-z0-9 _-]/g, "").replace(/\s+/g, "_") || "CV"}_CV.${format}`;

  return { blob, filename: backendName ?? fallback };
}
