PHASE 1 — PRE-EDIT AUDIT (files needing modification and why)
============================================================

Constraint check: clean tree (only ?? start-local.bat), no force-push,
no license change, no secrets. Full audit below.

A. PDF stack (PyMuPDF AGPL cleanup)
- backend/requirements.txt — WHY: pymupdf==1.28.2 is the only production
  runtime dep with AGPL/commercial licensing; pypdf (BSD-3) covers scorer
  text extraction. Remove pymupdf from runtime; move to optional dev note.
- backend/app/services/extractor.py — WHY: only production caller of
  fitz.open/get_text (scorer path). Replace with pypdf; keep caps/logging.
- backend/app/services/import_cv.py — WHY: _pdf_lines/_extract_entries_pages
  use fitz blocks/dict (font-size entry splitting). pypdf lacks per-span
  font size access; full replacement risks regression. Isolate: lazy-import
  pymupdf ONLY inside the PDF-import helpers, document why it stays, keep
  DOCX path dependency-free.
- backend/scripts/generate_template_previews.py — WHY: dev-only thumbnail
  renderer imports pymupdf at top level. Make import lazy (function-local)
  with friendly missing-dep message; never a runtime dep.
- backend/tests/test_import.py — WHY: test_scanned_pdf uses `import fitz`
  to build an empty PDF. Port to pypdf/reportlab so suite runs without
  pymupdf installed.
- CONTRIBUTING.md — WHY: thumbnail rule says `pip install pymupdf`; keep
  but scope as optional dev-only dep.
- README/docs — WHY: follow-up note + license/dependency table update.

B. Analytics removal (privacy-first)
- frontend/src/App.tsx — WHY: dead Plausible helper + 4 call sites
  (`plausible(...)`), but no Plausible <script> is ever loaded; calls are
  permanent no-ops inconsistent with privacy claims. Remove helper+calls.
- Legal.tsx / index.html — WHY: wording already claims no analytics; no
  change needed beyond keeping it true (no new provider).

C. Privacy wording fixes (accurate claims)
- README.md — WHY: "Your data never leaves the browser except to generate
  the file" + "no server-side storage" overstates: uploads ARE sent and
  held in memory; drafts in localStorage; provider logs exist. Reword to
  sent-for-processing / in-memory / not persisted.
- frontend/src/pages/Legal.tsx — WHY: mostly accurate; fix "can't leak
  because we never store it" + "no third-party data processing beyond
  hosting" to match in-memory processing over HTTPS.

D. Robots/sitemap placeholders
- frontend/public/robots.txt, frontend/public/sitemap.xml — WHY: contain
  YOUR_DOMAIN placeholder + TODO. Replace with __SITE_URL__ tokens.
- frontend/vite.config.ts — WHY: only replaces tokens in index.html; extend
  plugin to also emit robots.txt/sitemap.xml with resolved VITE_SITE_URL
  at build; same canonical URL; safe local fallback.
- README.md — WHY: document VITE_SITE_URL (required).

E. Docs/metadata/governance
- CODE_OF_CONDUCT.md (new), docs/CONTRIBUTOR_IDEAS.md (new),
  .github/dependabot.yml (new) — WHY: required by task phases 6/10/14.
- README.md + CONTRIBUTING.md — WHY: Discussions must be enabled in repo
  settings (can't be done in code); doc note + maintainer metadata block
  (description/topics) as suggestions only.
- frontend/src/App.tsx footer — WHY: "All rights reserved" conflicts with
  Apache-2.0; use Licensed under Apache-2.0 wording.

F. Dependencies/deploy (minimal, safe)
- backend/requirements.txt — WHY: swap pymupdf->pypdf for runtime; pin
  the rest unless a security patch is verified. DO NOT blindly upgrade.
- frontend/package.json — WHY: vitest ^2.1.9 only if safe patched minor
  is verified via npm; else keep.
- render.yaml — WHY: workers 2 -> 1 (small deploy), add .python-version
  pin (3.13.x), keep 0.0.0.0/$PORT/health/CORS-fail-fast.
- netlify.toml — WHY: already correct (base frontend, publish dist, SPA
  fallback, env-driven URLs); verify only.

G. Security review (no weakening)
- config.py/main.py/upload_guard.py/routes.py — WHY: CORS fail-fast,
  rate-limit, size caps, zip-bomb guard, no filename logging, generic
  500s verified intact; fix only if audit finds a hole (none found beyond
  phases above). No dangerouslySetInnerHTML; no temp files on CV paths.
