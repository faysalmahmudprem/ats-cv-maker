import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { downloadBlob, filenameFromDisposition } from "./download";

describe("filenameFromDisposition", () => {
  it("returns null for a missing header", () => {
    expect(filenameFromDisposition(null)).toBeNull();
  });

  it("parses a plain quoted filename", () => {
    expect(
      filenameFromDisposition('attachment; filename="Alex_Example_CV.docx"'),
    ).toBe("Alex_Example_CV.docx");
  });

  it("parses an unquoted filename", () => {
    expect(
      filenameFromDisposition("attachment; filename=CV_CV.pdf"),
    ).toBe("CV_CV.pdf");
  });

  it("prefers the RFC 5987 UTF-8 form and percent-decodes it", () => {
    // 🎉 percent-encoded — what the backend sends for non-ASCII names.
    const header =
      'attachment; filename="CV_CV.docx"; filename*=UTF-8\'\'%F0%9F%8E%89_CV.docx';
    expect(filenameFromDisposition(header)).toBe("🎉_CV.docx");
  });

  it("decodes other UTF-8 names (accented characters)", () => {
    const header = "attachment; filename*=UTF-8''Jos%C3%A9_Garc%C3%ADa_CV.docx";
    expect(filenameFromDisposition(header)).toBe("José_García_CV.docx");
  });

  it("falls back to the ASCII name when the UTF-8 form is malformed", () => {
    // %ZZ is not valid percent-encoding -> decodeURIComponent throws ->
    // the parser must fall back instead of crashing.
    const header =
      'attachment; filename="CV_CV.docx"; filename*=UTF-8\'\'%ZZ_CV.docx';
    expect(filenameFromDisposition(header)).toBe("CV_CV.docx");
  });
});

describe("downloadBlob", () => {
  let clicked: HTMLAnchorElement | null = null;
  const createObjectURL = vi.fn(() => "blob:mock-url");
  const revokeObjectURL = vi.fn();

  beforeEach(() => {
    clicked = null;
    // jsdom does not implement blob: URLs or anchor navigation.
    Object.defineProperty(URL, "createObjectURL", {
      value: createObjectURL,
      configurable: true,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      value: revokeObjectURL,
      configurable: true,
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(
      function (this: HTMLAnchorElement) {
        clicked = this;
      },
    );
  });

  afterEach(() => {
    delete (URL as unknown as Record<string, unknown>).createObjectURL;
    delete (URL as unknown as Record<string, unknown>).revokeObjectURL;
    vi.restoreAllMocks();
  });

  it("saves the blob under the given filename and revokes the URL", () => {
    const blob = new Blob(["docx-bytes"], {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });

    downloadBlob(blob, "Alex_Example_CV.docx");

    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(clicked).not.toBeNull();
    expect(clicked?.download).toBe("Alex_Example_CV.docx");
    expect(clicked?.href).toContain("blob:mock-url");
    // The object URL is released so the blob memory is not leaked.
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
  });
});
