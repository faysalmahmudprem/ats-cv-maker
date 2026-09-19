/**
 * CV import: upload an existing DOCX/PDF and get structured CV data back.
 * In-memory on the server; nothing is stored.
 */
import type { CVData } from "../types/cv";

const API_BASE: string = import.meta.env.VITE_API_URL ?? "";

export class ImportApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export interface ImportResult {
  cv: Partial<CVData>;
  warnings: string[];
  meta: {
    kind: string;
    filename: string;
    pages: number;
    words: number;
    sections_found: string[];
  };
}

export async function importCV(file: File): Promise<ImportResult> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 60_000);

  const body = new FormData();
  body.append("file", file);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/import-cv`, {
      method: "POST",
      body,
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ImportApiError("Reading your file took too long. Please try again.", 0);
    }
    throw new ImportApiError(
      `Cannot reach the server${API_BASE ? ` (${API_BASE})` : ""}. Check your connection and that the backend is running.`,
      0,
    );
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    let message = `Server error (HTTP ${res.status}).`;
    try {
      const data = await res.json();
      if (typeof data.error === "string") message = data.error;
      else if (typeof data.detail === "string") message = data.detail;
    } catch {
      /* keep generic */
    }
    throw new ImportApiError(message, res.status);
  }

  return (await res.json()) as ImportResult;
}
