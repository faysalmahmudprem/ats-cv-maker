# Security Policy

## Supported versions

This project is a small, stateless SaaS deployed as two services:

| Component | Location | Support |
| --------- | -------- | ------- |
| Frontend (React + Vite) | `frontend/` | Latest `main` only |
| Backend API (FastAPI)   | `backend/`  | Latest `main` only |

Only the latest version of `main` receives security fixes. There are no
release branches.

## Reporting a vulnerability

Please do **not** open a public GitHub issue for security problems.

Report vulnerabilities privately to:

**hello@faysalmahmudprem.com**

Include as much of the following as you can:

- A description of the issue and its potential impact.
- Step-by-step instructions or a proof of concept to reproduce it.
- The affected endpoint, page, or file.
- Any logs, screenshots, or request/response examples.

You will get an acknowledgement within **7 days** and progress updates at
least every 7 days until the issue is resolved or declined.

## Scope

The following are in scope:

- The FastAPI backend (`backend/app/**`) — its API endpoints, upload
  handling (DOCX/PDF import, CV scoring), request validation, and rate
  limiting.
- The React frontend (`frontend/src/**`) — client-side injection, unsafe
  DOM handling, and build/deploy configuration.
- Deployment configuration: `netlify.toml`, `render.yaml`, and the GitHub
  Actions workflow in `.github/workflows/`.

Please note this project is intentionally stateless: there are no user
accounts, no database, and no stored user data. Reports should focus on
what an attacker could do to **users of the deployed site** or to the
**hosting infrastructure**, for example:

- Crafting a malicious DOCX/PDF that escapes the upload guards
  (zip-bomb, path traversal, exhausted resources).
- Injecting content into generated files or the web UI.
- Bypassing rate limits or request-size caps to exhaust the free-tier
  backend.

## Out of scope

- Self-hosted deployments modified from this repository.
- Denial-of-service via sheer volume (use the rate limits responsibly).
- Missing security headers on third-party services (Netlify/Render) that
  are outside this repository's configuration.
- Vulnerabilities in dependencies with no practical exploit path in this
  app — still welcome as a report, but they will be handled as regular
  dependency updates.

## Safe harbor

Good-faith research that follows this policy is welcome. Please give a
reasonable amount of time for a fix before any public disclosure, and
avoid tests that degrade service for other users.
