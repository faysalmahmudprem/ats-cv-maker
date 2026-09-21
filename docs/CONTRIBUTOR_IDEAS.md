# Contributor ideas

Realistic, codebase-grounded ways to contribute. None of these are reported
bugs — they are small enhancements that fit the current architecture. Pick
one, open an issue or discussion first if it changes behavior, and keep
changes small and reviewable.

## New CV templates

- Add a `TemplateStyle` entry in `backend/app/templates.py` and mirror it in
  `frontend/src/data/templates.ts` (see `CONTRIBUTING.md` rule 2).
- Keep templates ATS-friendly: single column, no tables, no images, standard
  headings. Regenerate picker thumbnails per `CONTRIBUTING.md` rule 3.
- Add generator tests in `backend/tests/test_templates.py` covering the new
  template.

## Accessibility

- Audit form labels, focus order, and ARIA live regions (`StatusBanner`,
  draft-saved flash) with a screen reader.
- Check color contrast of template accents and status colors; fix in CSS.
- Verify keyboard-only flow: editor → preview → download works without a
  mouse, including the mobile Editor/Preview tab switch.

## Localization

- Extract hard-coded English strings in `frontend/src/` (form labels, FAQ,
  Legal pages) behind a small i18n dictionary.
- Start with one additional language; keep English as the fallback.
- Document the workflow for adding a language in `README.md`.

## Frontend tests

- Add Vitest + Testing Library coverage for `ScoreChecker`, `ImportCV`,
  and draft restore (`utils/storage`) edge cases.
- Test the mobile tab switch and the keyboard-aware fixed-bar hiding.
- Keep tests hermetic: mock `services/api` network calls.

## Backend tests

- Extend `backend/tests/test_import.py` with tricky real-world DOCX shapes
  (tables, wrapped contact lines, "Career Objective" headings).
- Add scorer regression cases in `backend/tests/test_scorer.py` for thin
  content (no bullets, missing email) so score behavior stays pinned.
- Cover upload-guard limits (`test_upload_guard.py`) for new archive shapes
  without weakening protections.

## PDF import improvements

- Structured PDF import (`backend/app/services/import_cv.py`) uses `pypdf`
  with structural entry-splitting heuristics (no font-size metadata —
  see the limitation note in that file). Improve two-column PDF reading
  order and wrapped-line contact recovery; leave fields empty rather
  than guessing when confidence is low. Verify against
  `backend/tests/test_import.py` before proposing changes.
- Improve two-column PDF reading order and wrapped-line contact recovery;
  leave fields empty rather than guessing when confidence is low.

## ATS scoring improvements

- Tune `backend/app/services/scorer.py` category weights against a small
  corpus of real CVs; document the rationale in the PR.
- Improve bullet/verb detection for non-English CVs without breaking
  existing English fixtures.
- Surface one additional actionable fix suggestion in the score response
  and mirror it in the `ScoreCard` UI.

## UI improvements

- Polish the live A4 preview (`CVPreview`) for long CVs: page-break hints,
  overflow warnings, print-friendly CSS.
- Improve empty states and error messages for failed imports/scores
  (corrupt file, scanned PDF) — keep them human, not technical.
- Small mobile-CSS wins: sticky download bar spacing, safe-area insets.

## Documentation

- Record common self-hosting pitfalls (CORS, `VITE_API_URL`, Render
  cold starts) in `README.md` troubleshooting notes.
- Add screenshots or short GIFs of the editor/preview flow.
- Keep `README.md`, `CONTRIBUTING.md`, and `frontend/src/pages/Legal.tsx`
  consistent on privacy claims after any behavior change.
