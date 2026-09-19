"""Generate template picker thumbnails (PNG) from the real generator.

For every registered template this script:
  1. builds a sample DOCX with the actual generator (so thumbnails always
     match real output),
  2. converts DOCX -> PDF with locally installed Microsoft Word (COM via
     scripts/docx2pdf.ps1),
  3. renders page 1 -> PNG with PyMuPDF into frontend/src/assets/templates/.

Run from the backend/ directory:
    python scripts/generate_template_previews.py

Requirements (dev only, never runtime deps): Microsoft Word installed,
`pip install pymupdf`. The produced PNGs ARE committed so the frontend
never needs Word or this script.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pymupdf

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.generator import generate_docx_bytes  # noqa: E402
from app.templates import TEMPLATES  # noqa: E402

OUT_DIR = BACKEND_DIR.parent / "frontend" / "src" / "assets" / "templates"
PS1 = Path(__file__).with_name("docx2pdf.ps1")

# Fictional sample CV used only for the thumbnails.
SAMPLE_CV = {
    "name": "Alex Example",
    "professional_title": "Software Engineer",
    "contact": {
        "location": "Dhaka, Bangladesh",
        "phone": "+880 1000-000000",
        "email": "alex@example.com",
        "linkedin": "linkedin.com/in/alexexample",
        "github": "github.com/alexexample",
        "portfolio": "",
    },
    "summary": (
        "Software engineer with experience building web applications "
        "and business software (ERP, POS, CRM)."
    ),
    "skills": [
        {"category": "Languages", "items": ["Python", "JavaScript", "PHP"]},
        {"category": "Frameworks", "items": ["FastAPI", "React", "Laravel"]},
    ],
    "experience": [
        {
            "title": "Software Engineer",
            "company": "Example Corp",
            "location": "Dhaka",
            "dates": "Jan 2024 - Present",
            "bullets": [
                "Built REST APIs serving 10k daily requests.",
                "Led migration of legacy ERP modules.",
                "Mentored two junior developers.",
            ],
        },
        {
            "title": "Junior Developer",
            "company": "Startup Co",
            "dates": "2022 - 2023",
            "bullets": ["Shipped the customer dashboard used by 500+ users."],
        },
    ],
    "projects": [
        {
            "name": "CV Generator",
            "technologies": ["Python", "python-docx"],
            "description": "Generates ATS-friendly Word CVs from JSON.",
            "details": [],
        }
    ],
    "education": [
        {
            "degree": "B.Sc. in Computer Science",
            "school": "Example University",
            "dates": "2019 - 2023",
            "details": [],
        }
    ],
    "certifications": [
        {"title": "AWS Cloud Practitioner", "issuer": "Amazon", "date": "2024"}
    ],
    "languages": ["English", "Bangla"],
    "additional_info": ["Open to relocation."],
}

PNG_DPI = 96  # A4 -> 794 x 1123 px


def render_png(pdf_path: Path, png_path: Path) -> None:
    with pymupdf.open(pdf_path) as pdf:
        page = pdf[0]
        pix = page.get_pixmap(dpi=PNG_DPI)
        pix.save(png_path)


def main() -> int:
    try:
        import pymupdf  # noqa: F401
    except ImportError:
        print("PyMuPDF missing. Run: pip install pymupdf")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="cv_previews_") as tmp:
        tmp_dir = Path(tmp)

        # 1) One DOCX per template, straight from the real generator.
        for key in TEMPLATES:
            (tmp_dir / f"{key}.docx").write_bytes(
                generate_docx_bytes(SAMPLE_CV, key)
            )

        # 2) DOCX -> PDF via Word COM.
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(PS1),
                "-Dir",
                str(tmp_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            print("Word COM conversion failed:")
            print(result.stdout)
            print(result.stderr)
            return 1
        print(result.stdout.strip())

        # 3) PDF -> PNG next to the frontend components.
        for key in TEMPLATES:
            pdf_path = tmp_dir / f"{key}.pdf"
            png_path = OUT_DIR / f"{key}.png"
            render_png(pdf_path, png_path)
            print(f"rendered: {png_path.relative_to(BACKEND_DIR.parent)}")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
