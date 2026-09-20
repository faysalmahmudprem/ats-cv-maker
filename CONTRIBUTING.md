# Contributing

Thanks for your interest in improving this project!

## Getting help: GitHub Discussions

Questions, ideas, design discussions, and announcements belong in
[GitHub Discussions](https://github.com/faysalmahmudprem/ats-cv-maker/discussions).

> Maintainer note: Discussions must be enabled in the repository's GitHub
> settings (Repo → Settings → General → Features → Discussions) — this
> cannot be configured from code. If the link above 404s, please open an
> issue and ask a maintainer to enable it.

## Reporting bugs and security issues

- **Bugs and feature requests:** open a GitHub issue using the provided
  templates.
- **Security vulnerabilities:** do **not** open a public issue. See
  [SECURITY.md](SECURITY.md) and email hello@faysalmahmudprem.com instead.

## Workflow: fork and branch

1. Fork the repository on GitHub.
2. Clone your fork locally.
3. Create a focused branch: `git checkout -b feat/short-description`.
4. Make small, reviewable changes (one concern per PR).
5. Push to your fork and open a pull request against `main`.

## Local setup

```bash
git clone https://github.com/faysalmahmudprem/ats-cv-maker
cd ats-cv-maker

# Backend (Python 3.11+, pinned via backend/.python-version)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (Node 18+), in a second terminal
cd frontend
npm install
npm run dev
```

Copy `frontend/.env.example` to `frontend/.env.local` for local overrides.
`VITE_API_URL` can stay empty locally (Vite dev proxy); set `VITE_SITE_URL`
only if you need to test canonical/robots/sitemap output.

## Frontend development

- React 18 + Vite 5 + TypeScript. Source lives in `frontend/src/`.
- API calls go through `frontend/src/services/api.ts` only.
- Commands (run in `frontend/`):
  - `npm run dev` — dev server with `/api` proxy to the backend.
  - `npm run typecheck` — TypeScript check.
  - `npm test` — Vitest suite.
  - `npm run build` — production build to `dist/` (also validates types).

## Backend development

- FastAPI + Pydantic v2. Source lives in `backend/app/`.
- PDF text extraction for ATS scoring uses `pypdf` (BSD-3-Clause).
  Structured PDF *import* still uses an optional PyMuPDF dependency (lazy
  import inside `backend/app/services/import_cv.py`) because `pypdf` does
  not expose the per-span font sizes that heuristic needs. DOCX import and
  ATS scoring work without PyMuPDF. See the follow-up note in `import_cv.py`
  before proposing a replacement — verify against `backend/tests/test_import.py`.
- Commands (run in `backend/`):
  - `uvicorn app.main:app --reload` — dev server.
  - `python -m pytest -v` — full backend suite.

## Test commands

```bash
cd backend && python -m pytest -v
cd frontend && npm run typecheck && npm test && npm run build
```

Run the relevant suite(s) before pushing; CI runs both on every push to
`main` and every pull request.

## Adding CV templates

1. Keep every template ATS-friendly: single column, no tables, no images.
2. Add new templates in `backend/app/templates.py` (one `TemplateStyle`
   entry) — the API schema and `GET /api/templates` pick it up
   automatically; mirror it in `frontend/src/data/templates.ts`.
3. **Template thumbnails:** regenerate the picker PNGs after changing a
   template's styling (requires Word + optional dev-only `pip install pymupdf`,
   never a production runtime dependency):

   ```bash
   cd backend && python scripts/generate_template_previews.py
   ```

   The script renders page 1 of each template's real DOCX via Word →
   PDF → PNG into `frontend/src/assets/templates/<key>.png`, and the
   updated PNGs are committed.
4. Add generator coverage in `backend/tests/test_templates.py`.
5. Run `python -m pytest` (in `backend/`) and `npm run build` (in
   `frontend/`) before pushing.
6. Keep generation logic (`backend/app/services/generator.py`) separate
   from HTTP code.
7. Never commit secrets, `.env` files, or generated `.docx` files.
8. Small focused commits, e.g. `feat: add projects form`.

## Sample data

The "See an example" content lives in `frontend/src/utils/sampleData.ts`
(experienced + fresher variants, fictional data only). It doubles as the
product's definition of "good": keep it scoring **95+** — 300+ words,
quantified achievements (`40%`, `200+ users`), action verbs, and full
sections. After changing it, verify with a generate → score round-trip
(DOCX should hit 100/A; PDF 95/A, since PDF bullets extract as a glyph
the scorer doesn't count — see `backend/app/services/scorer.py`).

Looking for ideas? See [docs/CONTRIBUTOR_IDEAS.md](docs/CONTRIBUTOR_IDEAS.md).

## Pull requests

- Keep PRs small and focused; one concern per PR.
- Describe what changed and why, plus test results (`pytest`, `typecheck`,
  `vitest`, `build` as applicable).
- Update `README.md` / docs when behavior, env vars, or privacy claims change.
- Confirm no secrets, `.env` files, or generated documents are included.
- Be ready to revise after review — CI must stay green.

## Security reporting

Do **not** open a public issue for vulnerabilities. Email
hello@faysalmahmudprem.com per [SECURITY.md](SECURITY.md) with a
description, impact, reproduction steps, and affected endpoint/page/file.

## License

By contributing, you agree that your contributions will be licensed under
the [Apache License 2.0](LICENSE) that covers this project. Please also
follow the [Code of Conduct](CODE_OF_CONDUCT.md).
