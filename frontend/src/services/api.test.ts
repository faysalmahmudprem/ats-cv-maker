/**
 * checkScore contract tests: the 15s abort ceiling, FormData wiring
 * (Blob gets a fallback filename so the backend picks the right
 * extractor), and the error path. Global fetch is stubbed; fake timers
 * drive the timeout deterministically.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { checkScore } from "./api";

function okResponse(body: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => body,
  } as unknown as Response;
}

const scoreBody = {
  score: 72,
  grade: "B",
  summary: "unused",
  categories: {},
  issues: [],
  fix_cta: false,
};

/** Fetch that hangs forever but rejects when its abort signal fires. */
function hangingFetch() {
  return vi.fn(
    (_url: string, init?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () =>
          reject(new DOMException("The operation was aborted.", "AbortError")),
        );
      }),
  );
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("checkScore", () => {
  it("aborts after 15 seconds when the server never answers", async () => {
    const fetchMock = hangingFetch();
    vi.stubGlobal("fetch", fetchMock);

    const pending = checkScore(new Blob(["cv"], { type: "application/pdf" }));
    // Attach the rejection handler BEFORE the abort fires — otherwise the
    // rejection lands in no handler's hands and vitest reports it as an
    // unhandled rejection between the microtask checkpoints.
    const expectation = expect(pending).rejects.toMatchObject({
      name: "AbortError",
    });

    // Still waiting just under the ceiling.
    await vi.advanceTimersByTimeAsync(14_999);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1);
    await expectation;
  });

  it("clears the timeout once the response arrives (no leaked timer)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => okResponse(scoreBody)),
    );

    await expect(checkScore(new File(["cv"], "Mine_CV.docx"))).resolves.toMatchObject({
      score: 72,
      grade: "B",
    });
    expect(vi.getTimerCount()).toBe(0);
  });

  it("sends the file as multipart form data under the 'file' field", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => okResponse(scoreBody));
    vi.stubGlobal("fetch", fetchMock);

    await checkScore(new File(["cv"], "Faysal_CV.pdf"));

    const [, init] = fetchMock.mock.calls[0];
    expect(init?.method).toBe("POST");
    const form = init?.body as FormData;
    expect(form).toBeInstanceOf(FormData);
    expect((form.get("file") as File).name).toBe("Faysal_CV.pdf");
  });

  it("names a nameless Blob 'CV.docx' so the backend uses the DOCX extractor", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => okResponse(scoreBody));
    vi.stubGlobal("fetch", fetchMock);

    await checkScore(new Blob(["docx-bytes"]));

    const form = fetchMock.mock.calls[0][1]?.body as FormData;
    expect((form.get("file") as File).name).toBe("CV.docx");
  });

  it("honors an explicit filename override (generate flow)", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => okResponse(scoreBody));
    vi.stubGlobal("fetch", fetchMock);

    await checkScore(new Blob(["pdf-bytes"], { type: "application/pdf" }), {
      filename: "Alex_Example_CV.pdf",
    });

    const form = fetchMock.mock.calls[0][1]?.body as FormData;
    expect((form.get("file") as File).name).toBe("Alex_Example_CV.pdf");
  });

  it("throws on a non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 500 }) as unknown as Response),
    );

    await expect(checkScore(new Blob(["x"]))).rejects.toThrow("Score check failed");
  });
});
