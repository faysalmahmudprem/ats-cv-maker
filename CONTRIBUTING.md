# Contributing

Thanks for your interest in improving this project!

## Reporting bugs and security issues

- **Bugs and feature requests:** open a GitHub issue using the provided
  templates.
- **Security vulnerabilities:** do **not** open a public issue. See
  [SECURITY.md](SECURITY.md) and email hello@faysalmahmudprem.com instead.

## Setup

```bash
git clone https://github.com/faysalmahmudprem/ats-cv-maker
cd ats-cv-maker

# Backend (Python 3.11+)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (Node 18+), in a second terminal
cd frontend
npm install
npm run dev
```

## Rules

1. Keep every template ATS-friendly: single column, no tables, no images.
2. Add new templates in `backend/app/templates.py` (one `TemplateStyle`
   entry) — the API schema and `GET /api/templates` pick it up
   automatically; mirror it in `frontend/src/data/templates.ts`.
3. **Template thumbnails:** regenerate the picker PNGs after changing a
   template's styling (requires Word + `pip install pymupdf`):

   ```bash
   cd backend && python scripts/generate_template_previews.py
   ```

   The script renders page 1 of each template's real DOCX via Word →
   PDF → PNG into `frontend/src/assets/templates/<key>.png`, and the
   updated PNGs are committed.
4. Run `python -m pytest` (in `backend/`) and `npm run build` (in
   `frontend/`) before pushing.
5. Keep generation logic (`backend/app/services/generator.py`) separate
   from HTTP code.
6. Never commit secrets, `.env` files, or generated `.docx` files.
7. Small focused commits, e.g. `feat: add projects form`.

## License

By contributing, you agree that your contributions will be licensed under
the [Apache License 2.0](LICENSE) that covers this project.
