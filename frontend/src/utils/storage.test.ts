import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearDraft,
  draftAgeMinutes,
  hasContent,
  loadDraft,
  saveDraft,
} from "./storage";
import { emptyCV } from "../types/cv";

const KEY = "cv_draft_v1";

/** Fresh Map-backed localStorage per test — no cross-test leakage. */
function memoryStorage() {
  const map = new Map<string, string>();
  return {
    getItem: (k: string) => (map.has(k) ? (map.get(k) as string) : null),
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
  };
}

beforeEach(() => {
  vi.stubGlobal("localStorage", memoryStorage());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function filledCV() {
  const cv = emptyCV();
  cv.name = "Alex Example";
  cv.professional_title = "Software Engineer";
  return cv;
}

describe("saveDraft / loadDraft round-trip", () => {
  it("restores exactly what was saved", () => {
    const cv = filledCV();
    saveDraft(cv);
    expect(loadDraft()).toEqual(cv);
  });

  it("returns null when nothing was saved", () => {
    expect(loadDraft()).toBeNull();
  });
});

describe("loadDraft guards", () => {
  it("rejects an unknown schema version", () => {
    localStorage.setItem(
      KEY,
      JSON.stringify({ version: 999, cv: filledCV(), savedAt: Date.now() }),
    );
    expect(loadDraft()).toBeNull();
  });

  it("rejects malformed JSON silently", () => {
    localStorage.setItem(KEY, "{not json");
    expect(loadDraft()).toBeNull();
  });

  it("rejects a draft without a cv object", () => {
    localStorage.setItem(KEY, JSON.stringify({ version: 1, savedAt: Date.now() }));
    expect(loadDraft()).toBeNull();
  });

  it("rejects a draft with no meaningful content", () => {
    // A saved empty CV must not come back as a "draft" offer.
    localStorage.setItem(
      KEY,
      JSON.stringify({ version: 1, cv: emptyCV(), savedAt: Date.now() }),
    );
    expect(loadDraft()).toBeNull();
  });

  it("merges partial drafts over the empty-CV defaults", () => {
    // Older or partial writes may miss fields added later; they must not
    // crash the editor — missing keys fill from emptyCV().
    localStorage.setItem(
      KEY,
      JSON.stringify({
        version: 1,
        cv: { name: "Alex", contact: { email: "alex@example.com" } },
        savedAt: Date.now(),
      }),
    );
    const draft = loadDraft();
    expect(draft).not.toBeNull();
    expect(draft?.name).toBe("Alex");
    expect(draft?.contact.email).toBe("alex@example.com");
    expect(draft?.contact.phone).toBe("");
    expect(Array.isArray(draft?.experience)).toBe(true);
  });
});

describe("saveDraft resilience", () => {
  it("does not throw when storage is unavailable (quota / private mode)", () => {
    vi.stubGlobal("localStorage", {
      getItem: () => null,
      setItem: () => {
        throw new Error("QuotaExceededError");
      },
      removeItem: () => {},
    });
    expect(() => saveDraft(filledCV())).not.toThrow();
  });
});

describe("clearDraft", () => {
  it("removes the draft", () => {
    saveDraft(filledCV());
    clearDraft();
    expect(loadDraft()).toBeNull();
  });

  it("does not throw when storage is unavailable", () => {
    vi.stubGlobal("localStorage", {
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {
        throw new Error("unavailable");
      },
    });
    expect(() => clearDraft()).not.toThrow();
  });
});

describe("hasContent", () => {
  it("is false for an empty CV", () => {
    expect(hasContent(emptyCV())).toBe(false);
  });

  it("detects content in any top-level field or contact detail", () => {
    const cv = emptyCV();
    cv.contact.location = "Dhaka";
    expect(hasContent(cv)).toBe(true);

    const cv2 = emptyCV();
    cv2.languages = ["English"];
    expect(hasContent(cv2)).toBe(true);

    const cv3 = emptyCV();
    cv3.professional_title = "Engineer";
    expect(hasContent(cv3)).toBe(true);
  });
});

describe("draftAgeMinutes", () => {
  it("is 0 for a just-saved draft", () => {
    expect(draftAgeMinutes(Date.now())).toBe(0);
  });

  it("rounds elapsed minutes", () => {
    const fiveMinutesAgo = Date.now() - 5 * 60_000;
    expect(draftAgeMinutes(fiveMinutesAgo)).toBe(5);
  });

  it("never goes negative (future clock skew)", () => {
    expect(draftAgeMinutes(Date.now() + 10 * 60_000)).toBe(0);
  });
});
