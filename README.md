<div align="center">

# ATS CV Generator

**Build an ATS-friendly CV in 2 minutes — download it as Word or PDF.**
Free · No signup · No paywall · No stored CVs

[![CI](https://github.com/faysalmahmudprem/ats-cv-maker/actions/workflows/ci.yml/badge.svg)](https://github.com/faysalmahmudprem/ats-cv-maker/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Node](https://img.shields.io/badge/Node-18%2B-339933?logo=nodedotjs&logoColor=white)

</div>

---

Fill in a structured form, watch a live A4 preview update as you type, and
download a clean `.docx` or PDF that applicant tracking systems (ATS) can
actually read. No accounts, no database, no stored CVs: CV data is sent
over HTTPS to the API only when needed — to generate a file, import an
existing CV, or score one — processed in memory, and never intentionally
persisted. Drafts stay in your own browser.

## ✨ Features

- **Structured CV editor** — personal info, summary, skills, experience,
  education, projects, certifications, languages, and additional info.
- **Live A4 preview** — mirrors the generated document as you type, in
  three templates: **Classic**, **Compact**, and **Modern**.
- **Real `.docx` + PDF export** — both formats render the same content in
  the same order from one shared layout definition, so they never drift.
- **ATS score checker** — upload any existing CV (DOCX/PDF) and get a
  0–100 score with a category breakdown and a prioritized fix list.
- **CV import** — upload an existing DOCX/PDF and the editor fills itself
  in. Parsed in memory; nothing is stored. Warnings flag anything the
  parser couldn't confidently recover.
- **Fresher / entry-level mode** — education and projects lead the CV,
  the summary becomes a "Career Objective", and work experience becomes
  optional (internships welcome).
- **Multiple skill groups** — Languages / Frameworks / Tools / … each
  render as their own CV line, with quick-pick category chips.
- **Per-bullet editing** — one input per achievement with add/remove and
  Enter-to-insert, instead of one big textarea.
- **Draft autosave** — drafts are stored in your own browser (debounced,
  never on a server) and offered back after a refresh.
- **Filled example in one click** — "See an example" loads a realistic
  sample CV (experienced and fresher variants) that models best practices:
  quantified achievements, full sections, 300+ words. It scores 100/A as
  DOCX and 95/A as PDF, so newcomers see what "good" looks like before
  typing a word.
- **Hardened API** — request size caps, a decompression-bomb guard on
  uploads, per-IP rate limiting on heavy endpoints, strict validation,
  and production CORS fail-fast.
- Works on **desktop and mobile** (Editor/Preview tab switch on small
  screens).

## ⚙️ How it works

```
Browser (React)               FastAPI backend               Output
┌──────────────┐  JSON/HTTPS  ┌────────────────────┐
│  Form editor │ ───────────► │ Validate (Pydantic)│
│  + preview   │              │ Build layout       │──► python-docx  → .docx
└──────────────┘              │ (shared by both    │──► ReportLab    → PDF
                              │  output formats)   │
Uploads (import/score):       └────────────────────┘
┌──────────────┐  file/HTTPS  ┌────────────────────┐
│  Existing CV  │ ───────────► │ In-memory parse /  │──► JSON result
│  (.docx/.pdf)│              │ ATS scoring        │    (never stored)
└──────────────┘              └────────────────────┘
```

The backend is **stateless**: no database, no accounts, no stored CVs.
Generating a CV is a pure function from JSON to file bytes, processed in
memory and never saved. Uploads (import/score) are likewise parsed in
memory and discarded; drafts stay in the browser's local storage.

## 🚀 Quick start

Prerequisites: **Python 3.11+** and **Node 18+**.

### 1. Start the backend

```bash
git clone https://github.com/faysalmahmudprem/ats-cv-maker
cd ats-cv-maker/backend

python -m venv .venv          # optional but recommended
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

The API is now on `http://127.0.0.1:8000` — interactive docs at
`http://127.0.0.1:8000/docs`.

### 2. Start the frontend (second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` to
`http://127.0.0.1:8000` automatically, so no extra configuration is
needed for local development.

## 📁 Project structure

```
ats-cv-maker/
├── frontend/                  # React + Vite + TypeScript app
│   ├── src/
│   │   ├── components/        # Form sections, preview, score & import UI
│   │   ├── services/          # API client (the only fetch() calls)
│   │   ├── types/             # CV data types mirroring backend schemas
│   │   ├── utils/             # validation, download, storage, sample data
│   │   ├── data/              # template & profile definitions (frontend)
│   │   └── pages/             # legal pages (privacy, terms)
│   ├── public/                # robots.txt, sitemap.xml, og-image
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── api/               # FastAPI routes, rate limiting
│   │   ├── schemas/           # Pydantic request models
│   │   ├── services/          # generator, PDF, import, scorer, layout
│   │   ├── templates.py       # template styles (add yours here)
│   │   ├── profiles.py        # experienced / fresher section order
│   │   └── main.py            # FastAPI app
│   ├── tests/                 # 126 pytest tests
│   └── requirements.txt
├── .github/                   # CI workflow, issue & PR templates
├── netlify.toml               # Netlify build + SPA config
├── render.yaml                # Render backend config
└── README.md
```

## 🧰 Tech stack

| Layer    | Technology                          |
| -------- | ----------------------------------- |
| Frontend | React 18, Vite 5, TypeScript, CSS   |
| Backend  | FastAPI, Pydantic v2, Uvicorn       |
| Document | python-docx (DOCX), ReportLab (PDF), pypdf (PDF text extraction & import) |
| Tests    | pytest + httpx · Vitest + Testing Library |
| Deploy   | Netlify (frontend), Render (backend) |
| CI       | GitHub Actions — both suites on every push & PR |

## 🔌 API endpoints

| Method | Endpoint              | Purpose                                        |
| ------ | --------------------- | ---------------------------------------------- |
| GET    | `/api/health`         | Health check (`{ "status": "ok" }`)            |
| GET    | `/api/templates`      | List available CV templates                    |
| POST   | `/api/generate-cv`    | Generate a CV file (`.docx` or PDF) from JSON  |
| POST   | `/api/import-cv`      | Parse an uploaded DOCX/PDF into editor data    |
| POST   | `/api/score-cv`       | Score an uploaded CV for ATS readiness (0–100) |

Upload and payload notes (verified against `backend/app/api/routes.py`
and `backend/app/config.py`):

- `POST /api/generate-cv` takes a JSON CV body (`name` required; all
  other fields optional; `template` defaults to `classic`, `profile` to
  `experienced`, `format` to `docx` or `pdf`). JSON bodies over
  `MAX_REQUEST_BYTES` (default 1 MB) are rejected with `413`; `422` on
  validation errors.
- `POST /api/import-cv` and `POST /api/score-cv` take one multipart
  `file` (`.pdf` or `.docx`, max `UPLOAD_MAX_BYTES`, default 5 MB —
  larger yields `413`). Unsupported types yield `415` (import) / `400`
  (score); empty or unreadable files yield `422` (import) / `500`
  (score). A text-less PDF (scan) imports as `422` with an honest
  "No text" message.
- `POST /api/import-cv` returns `{ cv, warnings, meta }`, where `meta`
  carries `kind`, `filename`, `pages`, `words`, and `sections_found`.
- `POST /api/score-cv` returns `{ score, grade, summary, categories,
  issues, word_count }`.

<details>
<summary><strong>Example: generate a CV (click to expand)</strong></summary>

```bash
curl -X POST http://127.0.0.1:8000/api/generate-cv \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alex Example",
    "professional_title": "Software Engineer",
    "contact": { "email": "alex@example.com" },
    "summary": "Backend engineer with 5 years of experience…",
    "skills": [{ "category": "Languages", "items": ["Python", "Go"] }],
    "experience": [{
      "title": "Software Engineer",
      "company": "Example Corp",
      "dates": "2021 — Present",
      "bullets": ["Cut API latency 40% by…"]
    }]
  }' -o Alex_Example_CV.docx
```

All fields except `name` are optional. `template` defaults to `classic`,
`profile` to `experienced`, and `format` to `docx` (or `pdf`).

Responses: `200` returns the file as an attachment · `422` validation
error with JSON detail · `413` request body too large.

</details>

<details>
<summary><strong>Example: score an existing CV</strong></summary>

```bash
curl -X POST http://127.0.0.1:8000/api/score-cv -F "file=@my_cv.pdf"
```

Returns a total score, per-category breakdown, and a human-readable fix
list. Uploads are limited to 5 MB and parsed entirely in memory.

</details>

## 🧪 Testing

```bash
# Backend — 126 tests (generator, API, templates, profiles, PDF,
# import, scoring, rate limiting, upload safety, security regressions)
cd backend
pip install -r requirements.txt
python -m pytest -v

# Frontend — 71 tests + typecheck + production build
cd frontend
npm install
npm test
npm run typecheck
npm run build
```

CI runs both suites on every push to `main` and every pull request.

## 🌍 Environment variables

### Frontend

| Variable       | Where                 | Purpose                                                                 |
| -------------- | --------------------- | ----------------------------------------------------------------------- |
| `VITE_API_URL` | `.env.local`, Netlify | Base URL of the backend. Leave empty locally to use the dev proxy.       |
| `VITE_SITE_URL`| `.env.local`, Netlify | Public frontend URL — used at build time for canonical/og:image tags, robots.txt, and sitemap.xml. Optional locally (falls back to `http://localhost:5173`); set it in Netlify for production. |

See `frontend/.env.example`.

> `VITE_*` values are baked into the frontend bundle at build time —
> never put secrets in them.

### Backend

| Variable             | Default (local)      | Purpose                                   |
| -------------------- | -------------------- | ----------------------------------------- |
| `CORS_ORIGINS`       | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed browser origins |
| `MAX_REQUEST_BYTES`  | `1000000`            | Reject JSON bodies larger than this       |
| `UPLOAD_MAX_BYTES`   | `5000000`            | Reject import/score uploads larger than this |
| `MAX_EXTRACT_CHARS`  | `200000`             | Cap on text extracted from an upload      |
| `RATE_LIMIT_ENABLED` | `1`                  | Per-IP limiting of heavy endpoints (0 = off) |
| `RATE_LIMIT_PER_MINUTE` | `30`              | Requests per minute per IP                |
| `TRUST_XFF` | `1` | Trust X-Forwarded-For for rate-limit IP (set 0 if not behind a trusted proxy) |
| `ENVIRONMENT`        | `development`        | Informational                             |

No secrets are required — the app stores no CVs.

> Local vs production: the defaults above are for local development.
> In production (`ENVIRONMENT=production`) the backend refuses to start
> unless `CORS_ORIGINS` is explicitly set to the deployed frontend
> origin(s).

## ☁️ Deployment

### Frontend → Netlify

1. Push the repository to GitHub.
2. In Netlify: **Add new site → Import an existing project** and pick the repo.
3. Netlify reads `netlify.toml` automatically (base `frontend`, build
   `npm run build`, publish `dist` — relative to the `frontend/` base).
4. Set `VITE_API_URL` to your backend URL, e.g.
   `https://ats-cv-maker-api.onrender.com` (no trailing slash).
5. Set `VITE_SITE_URL` to your frontend URL, e.g.
   `https://your-site.netlify.app` (no trailing slash) — this fills the
   canonical URL, social preview image, `robots.txt`, and `sitemap.xml`
   at build time.
6. Deploy.

### Backend → Render

1. In Render: **New → Web Service** and pick the repository.
2. Render detects `render.yaml`: root dir `backend`, build
   `pip install -r requirements.txt`, start
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`.
   Python is pinned via `backend/.python-version`.
3. Set `CORS_ORIGINS` to your Netlify origin, e.g.
   `https://your-site.netlify.app`.
4. Deploy. Health check path: `/api/health`.

> **Free-tier tip:** free Render instances sleep after ~15 min idle, so
> the first download can take ~30–60 s (the first `/api/health` call may
> return `503` while the service wakes). A free cron ping to
> `/api/health` (e.g. cron-job.org) mitigates this.

### Live backend

The backend is deployed on Render:

- App: `https://ats-cv-maker-api.onrender.com`
- Health: `https://ats-cv-maker-api.onrender.com/api/health`
- API docs: `https://ats-cv-maker-api.onrender.com/docs`
- OpenAPI: `https://ats-cv-maker-api.onrender.com/openapi.json`

Frontend deployment: pending — no production frontend URL yet, so set
`VITE_API_URL` to the Render URL above when deploying the frontend.

### 🔧 Troubleshooting

- **Backend slow or `503` on first request:** free Render instances sleep
  when idle; wait ~30–60 s and retry `/api/health`.
- **CORS errors in the browser:** the deployed frontend origin must be in
  the backend's `CORS_ORIGINS`; production refuses to start without it.
- **Frontend can't reach the API:** check `VITE_API_URL` (no trailing
  slash) — it is baked in at build time, so changing it requires a
  rebuild/redeploy of the frontend.
- **Netlify build failure:** ensure base is `frontend`, build command is
  `npm run build`, and both `VITE_API_URL` and `VITE_SITE_URL` are set in
  the Netlify UI.

## 🤝 Contributing

Contributions are welcome! Start with
[CONTRIBUTING.md](CONTRIBUTING.md) for setup, project rules (how to add a
template, where generation logic lives), and the pre-push checklist.
Good first issues are labeled `good first issue`. Ideas live in
[docs/CONTRIBUTOR_IDEAS.md](docs/CONTRIBUTOR_IDEAS.md). Please follow the
[Code of Conduct](CODE_OF_CONDUCT.md).

- 🐛 [Report a bug](.github/ISSUE_TEMPLATE/bug_report.yml)
- 💡 [Suggest a feature](.github/ISSUE_TEMPLATE/feature_request.yml)
- 💬 [GitHub Discussions](https://github.com/faysalmahmudprem/ats-cv-maker/discussions) — questions, ideas, and community conversations.
  Maintainer note: Discussions must be enabled in GitHub repository
  settings (Repo → Settings → General → Features); code cannot enable it.
- 🔒 Security vulnerabilities go to **hello@faysalmahmudprem.com** — see
  [SECURITY.md](SECURITY.md). Please don't open public issues for them.

## 🗺️ Roadmap

Ideas, not yet implemented: user accounts and saved CVs, AI writing
assistant, job-description keyword matching, more templates and languages.

## 📄 License

Released under the [Apache License 2.0](LICENSE).

## 🏷️ Maintainer note: GitHub metadata (manual setup)

Repository settings cannot be changed from code — a maintainer should set
these in the GitHub UI (Repo → Settings / About):

Suggested description:

> Open-source ATS-friendly CV builder with React + FastAPI, DOCX/PDF export, CV import, and ATS scoring.

Suggested topics:

`ats`, `cv-builder`, `cv-generator`, `resume-builder`, `resume-generator`,
`react`, `typescript`, `fastapi`, `python`, `python-docx`, `open-source`

These are suggestions only; they are not claimed to be already configured.
