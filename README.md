# CV Generator SaaS

Free, ATS-friendly CV generator. Fill in a form, watch a live preview,
download a clean `.docx` file in seconds. No signup, no paywall, no data
storage.

**Deploy:** Netlify (frontend) + Render (backend) — see below
**API docs:** once the backend is running, open `http://localhost:8000/docs`

---

## Features

- Structured CV editor: personal info, summary, skills, experience,
  education, projects, certifications, languages, additional info.
- **Multiple skill groups** (Languages / Frameworks / Tools / …) with
  quick-pick category chips — each group renders as its own CV line.
- **Per-bullet editing** — one input per achievement with add/remove and
  Enter-to-insert, instead of one-big-textarea.
- **Fresher / Entry-level mode** — education and projects lead the CV,
  the summary becomes a "Career Objective", and work experience becomes
  optional (internships welcome). Experienced mode stays the default.
- Add / edit / remove / reorder entries, with multiple bullet points per job.
- **Multiple CV templates** — Classic, Compact and Modern, with a live
  preview that reflects the selected template.
- Live A4 preview that mirrors the generated document as you type.
- ATS readiness checklist (single column, real text, keywords).
- Editor progress nav with completion ticks, next-section flow, and a
  mobile **Editor/Preview** tab switch.
- One-click **`.docx` and PDF** generation with a clean, ATS-safe layout
  (both formats render the same content and section order).
- **Draft autosave** — your entries are stored in your own browser
  (debounced, never on a server) and offered back after a refresh.
- Hardened API: request size caps (including chunked bodies), a
  decompression-bomb guard on uploads, per-IP rate limiting on the heavy
  endpoints, strict Pydantic validation, generic error messages, and
  production CORS fail-fast.
- **CV import** — upload an existing DOCX or PDF and the editor fills
  itself in (parsed in memory, nothing stored, warnings for anything the
  parser couldn't confidently recover).
- Works on desktop and mobile.

## Tech stack

| Layer    | Technology                          |
| -------- | ----------------------------------- |
| Frontend | React 18, Vite 5, TypeScript, CSS   |
| Backend  | FastAPI, Pydantic v2, Uvicorn       |
| Document | python-docx (DOCX), ReportLab (PDF) |
| Tests    | pytest + httpx (backend)            |
| Deploy   | Netlify (frontend), Render (backend)|

## Architecture

```
Browser (React)  →  POST /api/generate-cv (JSON)  →  FastAPI validates (Pydantic)
                 →  python-docx builds the file   →  DOCX bytes returned
                 →  Browser downloads the .docx
```

The backend is stateless: nothing is stored, no database required.

## Project structure

```
ats-cv-maker/
├── frontend/               # React + Vite + TypeScript app
│   ├── src/
│   │   ├── components/     # Reusable UI + form section components
│   │   ├── services/       # API client (the only fetch() calls)
│   │   ├── types/          # CV data types mirroring backend schemas
│   │   ├── utils/          # validation, download, sample data
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routes
│   │   ├── schemas/        # Pydantic request models
│   │   ├── services/       # DOCX generator (python-docx)
│   │   ├── config.py       # Environment-based settings
│   │   └── main.py         # FastAPI app
│   ├── tests/              # pytest suite (generator + API)
│   ├── requirements.txt
│   └── pytest.ini
├── netlify.toml            # Netlify build + SPA config
├── render.yaml             # Render backend config
└── README.md
```

## Local setup

Prerequisites: **Python 3.11+** and **Node 18+**.

### Backend

```bash
cd backend
python -m venv .venv                 # optional but recommended
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is now on `http://127.0.0.1:8000` (interactive docs at `/docs`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app is now on `http://localhost:5173`. By default the Vite dev server
proxies `/api` to `http://127.0.0.1:8000`, so no extra configuration is
needed for local development.

## Environment variables

### Frontend

| Variable       | Where                | Purpose                                             |
| -------------- | -------------------- | --------------------------------------------------- |
| `VITE_API_URL` | `.env.local`, Netlify| Base URL of the backend. Leave empty locally to use the dev proxy. Set to your backend URL in production. |
| `VITE_SITE_URL`| `.env.local`, Netlify| Public frontend URL, used at build time for `canonical` / `og:image` in `index.html` (see the `site-url` plugin in `vite.config.ts`). Optional locally. |

See `frontend/.env.example`.

### Backend

| Variable            | Default (local)                          | Purpose                                   |
| ------------------- | ---------------------------------------- | ----------------------------------------- |
| `CORS_ORIGINS`      | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed browser origins |
| `MAX_REQUEST_BYTES` | `1000000`                                | Reject JSON bodies larger than this       |
| `UPLOAD_MAX_BYTES`  | `5000000`                                | Reject import/score uploads larger than this |
| `MAX_EXTRACT_CHARS` | `200000`                                 | Cap on text extracted from an upload      |
| `MAX_ARCHIVE_ENTRIES` | `5000`                                 | Reject a DOCX with too many internal parts |
| `MAX_ARCHIVE_UNCOMPRESSED_BYTES` | `50000000`                  | Reject a DOCX that expands beyond this    |
| `MAX_ARCHIVE_RATIO` | `200`                                    | Reject suspicious compression ratios      |
| `RATE_LIMIT_ENABLED` | `1`                                     | Per-IP limiting of heavy endpoints (0 = off) |
| `RATE_LIMIT_PER_MINUTE` | `30`                                 | Requests per minute per IP                |
| `ENVIRONMENT`       | `development`                            | Informational                             |
| `APP_NAME`          | `CV Generator API`                       | Shown in API docs                         |

No secrets are required — the app stores nothing.

## API endpoints

### `GET /api/health`

```json
{ "status": "ok" }
```

### `GET /api/templates`

Lists the available CV templates:

```json
{
  "templates": [
    { "key": "classic", "label": "Classic", "description": "…", "accent_hex": "#1F3B63" },
    { "key": "compact", "label": "Compact", "description": "…", "accent_hex": "#333333" },
    { "key": "modern", "label": "Modern", "description": "…", "accent_hex": "#0F766E" }
  ]
}
```

### `POST /api/import-cv`

Multipart upload of an existing CV file; returns structured data for the
editor. In-memory only — the file is parsed and discarded.

```bash
curl -X POST http://127.0.0.1:8000/api/import-cv -F "file=@my_cv.docx"
```

```json
{
  "cv": { "name": "…", "experience": [ … ] },
  "warnings": ["No email found — add it in Personal information."],
  "meta": { "kind": "docx", "pages": 1, "words": 412, "sections_found": ["experience", "education"] }
}
```

Responses: `200` parsed (+ human-readable `warnings`) · `413` file too
large (`UPLOAD_MAX_BYTES`, default 5 MB) · `415` unsupported type · `422`
unreadable/corrupt/empty file.

### `POST /api/generate-cv`

Request body (all fields optional except `name`; `template` defaults to
`classic`, `profile` to `experienced`, `format` to `docx`):

```json
{
  "profile": "experienced",
  "template": "classic",
  "format": "docx",
  "name": "Alex Example",
  "professional_title": "Software Engineer",
  "contact": {
    "location": "Dhaka, Bangladesh",
    "phone": "+880 1000-000000",
    "email": "alex@example.com",
    "linkedin": "linkedin.com/in/alexexample",
    "github": "github.com/alexexample",
    "portfolio": "alexexample.dev"
  },
  "summary": "…",
  "skills": [{ "category": "Languages", "items": ["Python", "JavaScript"] }],
  "experience": [
    { "title": "…", "company": "…", "location": "…", "dates": "…", "bullets": ["…"] }
  ],
  "projects": [{ "name": "…", "technologies": ["…"], "description": "…", "details": ["…"] }],
  "education": [{ "degree": "…", "school": "…", "location": "…", "dates": "…", "details": ["…"] }],
  "certifications": [{ "title": "…", "issuer": "…", "date": "…" }],
  "languages": ["English", "Bangla"],
  "additional_info": ["…"]
}
```

Responses:

- `200` — the generated file (`Content-Disposition: attachment`, filename
  like `Alex_Example_CV.docx` or `Alex_Example_CV.pdf`)
- `422` — validation error with JSON detail (including an unknown `template`,
  `profile` or `format`)
- `413` — request body too large

Quick test with curl:

```bash
curl -X POST http://127.0.0.1:8000/api/generate-cv \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Person","contact":{"email":"t@example.com"}}' \
  -o test_cv.docx
```

## Testing

Backend (115 tests: generator, API, templates, profiles, PDF, import,
scoring, rate limiting, upload safety, security regressions):

```bash
cd backend
pip install -r requirements.txt
python -m pytest -v
```

Frontend unit tests (71 tests), type-check and production build:

```bash
cd frontend
npm test
npm run typecheck
npm run build
```

CI (GitHub Actions) runs both on every push and pull request — see
`.github/workflows/ci.yml`.

## Deployment

### Frontend → Netlify

1. Push the repository to GitHub.
2. In Netlify: **Add new site → Import an existing project** and pick the repo.
3. Netlify reads `netlify.toml` automatically (base `frontend`, build
   `npm run build`, publish `frontend/dist`).
4. Set the environment variable **`VITE_API_URL`** to your backend URL, e.g.
   `https://cv-generator-api.onrender.com` (no trailing slash).
5. Deploy.

### Backend → Render

1. In Render: **New → Web Service** and pick the repository.
2. Render detects `render.yaml`: root dir `backend`, build
   `pip install -r requirements.txt`, start
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`.
3. Set the environment variable **`CORS_ORIGINS`** to your Netlify origin,
   e.g. `https://your-site.netlify.app`.
4. Deploy. The health check path is `/api/health`.

The same approach works on Railway/Fly.io/PythonAnywhere: install
`requirements.txt` and run the uvicorn command with the platform's `PORT`.

## Before you launch (checklist)

- [x] **Contact email:** set to `hello@faysalmahmudprem.com` in
      `frontend/src/pages/Legal.tsx` (both the Privacy Policy and the Terms
      of Service).
- [ ] **Review the legal copy:** it honestly describes the current behavior
      (no storage, browser-only drafts, no analytics). Revisit it if you add
      accounts, analytics, or error reporting — update the pages *before*
      shipping such a change.
- [ ] **Hosting region / provider:** the privacy page mentions "a commercial
      cloud provider" — name it (e.g. Render) if you prefer explicit wording.
- [ ] **SEO domain:** set `VITE_SITE_URL` (e.g. in the Netlify UI) so the
      `canonical` / `og:image` tags in `frontend/index.html` resolve to your
      final URL, and replace the `YOUR_DOMAIN` placeholder in
      `frontend/public/robots.txt` and `frontend/public/sitemap.xml`.
- [ ] **Keep-alive:** free Render instances sleep after ~15 min idle; the
      first download can take ~30–60 s. A free cron ping to `/api/health`
      (e.g. cron-job.org) mitigates this.

## Future roadmap

Ideas (not yet implemented): user accounts and saved CVs, PDF export,
AI writing assistant, job-description keyword matching, premium features.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security vulnerabilities are
handled privately — see [SECURITY.md](SECURITY.md).

## License

Released under the [Apache License 2.0](LICENSE).
