"""Pytest fixtures shared across backend tests.

Tests run from the backend/ directory (see backend/pytest.ini) so that
`import app...` resolves without any installation step.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

# Ensure the backend directory is on sys.path no matter where pytest runs.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# The rate limiter is in-process and would trip on a fast test run, so it is
# disabled for the functional suite. Its behaviour is covered directly in
# tests/test_rate_limit.py, which builds its own app instance.
os.environ.setdefault("RATE_LIMIT_ENABLED", "0")

from app.main import app  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def sample_cv() -> Dict[str, Any]:
    """Complete, valid sample CV. Fictional data — not real personal info."""
    return {
        "name": "Alex Example",
        "professional_title": "Software Engineer",
        "contact": {
            "location": "Dhaka, Bangladesh",
            "phone": "+880 1000-000000",
            "email": "alex@example.com",
            "linkedin": "linkedin.com/in/alexexample",
            "github": "github.com/alexexample",
            "portfolio": "alexexample.dev",
        },
        "summary": "Software engineer with experience building web applications and business software.",
        "skills": [
            {"category": "Languages", "items": ["Python", "JavaScript"]},
            {"category": "Frameworks", "items": ["FastAPI", "React"]},
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
                ],
            }
        ],
        "projects": [
            {
                "name": "CV Generator",
                "technologies": ["Python", "python-docx"],
                "description": "Generates ATS-friendly Word CVs from JSON.",
                "details": ["Supports Unicode text and hyperlinks."],
            }
        ],
        "education": [
            {
                "degree": "B.Sc. in Computer Science",
                "school": "Example University",
                "location": "Dhaka",
                "dates": "2019 - 2023",
                "details": ["CGPA 3.80/4.00"],
            }
        ],
        "certifications": [
            {"title": "AWS Cloud Practitioner", "issuer": "Amazon", "date": "2024"}
        ],
        "languages": ["English", "Bangla"],
        "additional_info": ["Open to relocation."],
    }
