"""
Rule-based ATS scoring engine.

Pure functions: text in, score dict out. No ML, no external APIs, no I/O.
Score six categories totalling 100 points and generate a severity-ordered
issues list with actionable fixes.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Detection assets
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
YEAR_RE = re.compile(r"(20\d{2}|19\d{2})")
QUANT_RE = re.compile(r"\d+\s?%|\$\s?\d[\d,.]*\s?[kKmM]?|\b\d+\+|\b\d+x\b")

ACTION_VERBS = [
    "led", "built", "developed", "managed", "created", "designed",
    "implemented", "improved", "increased", "reduced", "achieved",
    "delivered", "launched", "coordinated", "optimized",
]

TECH_KEYWORDS = [
    "javascript", "python", "php", "react", "laravel", "django", "mysql",
    "postgresql", "api", "rest", "git", "docker", "aws", "linux",
    "typescript", "node", "sql",
]

SOFT_SKILLS = [
    "team", "communication", "leadership", "collaboration", "problem",
    "analytical", "stakeholder", "cross-functional",
]

BOX_CHARS = ["│", "┌", "╔"]
BULLET_MARKS = ["•", "-", "▪"]

SECTION_HEADINGS = [
    "experience", "education", "skills", "summary", "objective",
    "projects", "certifications",
]

# ---------------------------------------------------------------------------
# Category scorers — each returns (points_awarded, max_points, failed_checks)
# where failed_checks is a list of (severity, title, detail, fix) tuples.
# ---------------------------------------------------------------------------


def _score_format(text: str) -> tuple[int, int, List[tuple[str, str, str, str]]]:
    max_pts = 20
    score = max_pts
    issues: List[tuple[str, str, str, str]] = []

    has_box_chars = any(ch in text for ch in BOX_CHARS)
    first_100 = text[:100]
    no_alnum_start = not any(c.isalnum() for c in first_100)
    word_count = len(text.split())

    if has_box_chars:
        score -= 10
        issues.append((
            "high",
            "Complex formatting detected",
            "Your CV contains table or box-drawing characters that ATS parsers cannot read.",
            "Remove tables and text boxes — ATS cannot read them",
        ))
    if "[image]" in text or no_alnum_start:
        score -= 5
    if word_count < 100:
        score -= 5

    return max(score, 0), max_pts, issues


def _score_contact(text: str) -> tuple[int, int, List[tuple[str, str, str, str]]]:
    max_pts = 15
    score = 0
    issues: List[tuple[str, str, str, str]] = []

    has_email = bool(EMAIL_RE.search(text))
    has_phone = bool(PHONE_RE.search(text))
    has_linkedin = "linkedin.com" in text.lower()

    if has_email:
        score += 5
    else:
        issues.append((
            "high",
            "Email address missing",
            "No email address was found anywhere in the document.",
            "Add your email to the contact section",
        ))
    if has_phone:
        score += 5
    else:
        issues.append((
            "high",
            "Phone number missing",
            "No phone number was found anywhere in the document.",
            "Add your phone number to the contact section",
        ))
    if has_linkedin:
        score += 5
    else:
        issues.append((
            "medium",
            "LinkedIn URL missing",
            "Recruiters expect a LinkedIn profile alongside your CV.",
            "Add linkedin.com/in/yourname to contacts",
        ))

    return score, max_pts, issues


def _score_keywords(text: str) -> tuple[int, int, List[tuple[str, str, str, str]]]:
    max_pts = 25
    score = 0
    issues: List[tuple[str, str, str, str]] = []
    lower = text.lower()

    action_hits = sum(1 for verb in ACTION_VERBS if verb in lower)
    if action_hits > 0:
        score += 5
    else:
        issues.append((
            "high",
            "No achievement language detected",
            "Bullet points read as duties rather than achievements.",
            "Start bullet points with action verbs: Led, Built, Increased, Reduced",
        ))

    tech_hits = sum(1 for kw in TECH_KEYWORDS if kw in lower)
    if tech_hits >= 3:
        score += 10
    elif tech_hits > 0:
        score += 5
    else:
        issues.append((
            "medium",
            "No technical skills detected",
            "No tools, languages or technologies were found in the text.",
            "Add a Skills section listing your tools and technologies",
        ))

    if any(sk in lower for sk in SOFT_SKILLS):
        score += 5

    if QUANT_RE.search(text):
        score += 5
    else:
        issues.append((
            "medium",
            "No measurable results",
            "Achievements contain no numbers, so impact is hard to judge.",
            "Add numbers: '30% faster', '200+ users', '$10k saved'",
        ))

    return score, max_pts, issues


def _score_experience(text: str) -> tuple[int, int, List[tuple[str, str, str, str]]]:
    max_pts = 20
    score = 0
    issues: List[tuple[str, str, str, str]] = []
    lower = text.lower()

    if any(h in lower for h in ("experience", "employment", "work history")):
        score += 5
    date_count = len(YEAR_RE.findall(text))
    if date_count >= 2:
        score += 10
    else:
        issues.append((
            "medium",
            "Work dates unclear",
            "Fewer than two year references were found, so timelines are ambiguous.",
            "Add clear date ranges: 'Jan 2022 – Present'",
        ))

    lines = text.split("\n")
    bullet_lines = sum(
        1
        for line in lines
        if any(line.strip().startswith(mark) for mark in BULLET_MARKS)
        or line.strip().startswith("*")
    )
    if bullet_lines >= 3:
        score += 5
    else:
        issues.append((
            "medium",
            "Missing achievement bullets",
            "Fewer than three bullet-style lines were detected.",
            "Use bullet points for each job responsibility",
        ))

    return score, max_pts, issues


def _score_length(text: str) -> tuple[int, int, List[tuple[str, str, str, str]]]:
    max_pts = 10
    word_count = len(text.split())
    issues: List[tuple[str, str, str, str]] = []

    if 300 <= word_count <= 900:
        score = 10
    elif 900 < word_count <= 1400:
        score = 8
    elif 200 <= word_count < 300:
        score = 5
    elif word_count > 1400:
        score = 4
        issues.append((
            "low",
            "CV may be too long",
            f"The document runs {word_count} words, beyond the 2-page norm.",
            "Trim to 1–2 pages (300–900 words) for best ATS results",
        ))
    else:  # < 200 words
        score = 0
        issues.append((
            "high",
            "CV is too short",
            f"Only {word_count} words were found — far below a substantive CV.",
            "Add more detail — aim for 300–900 words",
        ))

    return score, max_pts, issues


def _score_headings(text: str) -> tuple[int, int, List[tuple[str, str, str, str]]]:
    max_pts = 10
    lower = text.lower()
    found = 0
    for heading in SECTION_HEADINGS:
        if heading in lower:
            # "summary" and "objective" share one 2-pt slot.
            if heading in ("summary", "objective"):
                if "summary" in lower or "objective" in lower:
                    pass  # counted once below
                continue
            found += 1
    if "summary" in lower or "objective" in lower:
        found += 1
    score = min(found * 2, max_pts)

    issues: List[tuple[str, str, str, str]] = []
    if found < 3:
        issues.append((
            "medium",
            "Missing standard sections",
            f"Only {found} standard section heading(s) were detected.",
            "Add clear headings: Experience, Education, Skills, Summary",
        ))
    return score, max_pts, issues


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _status(score: int, max_pts: int) -> str:
    if max_pts == 0:
        return "good"
    pct = score / max_pts
    if pct >= 0.75:
        return "good"
    if pct >= 0.40:
        return "warning"
    return "poor"


def grade_for(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def summarize(score: int, grade: str) -> str:
    verdicts = {
        "A": "Excellent — this CV should pass ATS screening with room to spare.",
        "B": "Good — a few targeted improvements will make this very strong.",
        "C": "Fair — several common ATS issues are costing you points.",
        "D": "Weak — an ATS is likely to misread important parts of this CV.",
        "F": "Poor — this CV will likely fail ATS parsing as it stands.",
    }
    return verdicts.get(grade, verdicts["F"])


def score_cv_text(text: str) -> Dict[str, Any]:
    """Score extracted CV text and return the full score dict."""
    word_count = len(text.split())

    # An empty extraction has nothing to score: the literal format rules
    # would still award 10/20 (no box chars, no content to offend), which
    # is nonsense — report a clean zero instead.
    if word_count == 0:
        return {
            "score": 0,
            "grade": "F",
            "summary": summarize(0, "F"),
            "categories": {
                key: {"score": 0, "max": max_pts, "status": "poor"}
                for key, max_pts in (
                    ("format", 20),
                    ("contact", 15),
                    ("keywords", 25),
                    ("experience", 20),
                    ("length", 10),
                    ("headings", 10),
                )
            },
            "issues": [
                {
                    "severity": "high",
                    "title": "CV is too short",
                    "detail": "No readable text was found in the document.",
                    "fix": "Add more detail — aim for 300–900 words",
                }
            ],
            "word_count": 0,
            "fix_cta": True,
        }

    results = {
        "format": _score_format(text),
        "contact": _score_contact(text),
        "keywords": _score_keywords(text),
        "experience": _score_experience(text),
        "length": _score_length(text),
        "headings": _score_headings(text),
    }

    categories: Dict[str, Dict[str, Any]] = {}
    issues: List[Dict[str, str]] = []
    total = 0
    for key, (pts, max_pts, raw_issues) in results.items():
        total += pts
        categories[key] = {
            "score": pts,
            "max": max_pts,
            "status": _status(pts, max_pts),
        }
        for severity, title, detail, fix in raw_issues:
            issues.append(
                {"severity": severity, "title": title, "detail": detail, "fix": fix}
            )

    issues.sort(key=lambda i: _SEVERITY_ORDER.get(i["severity"], 3))

    score = min(total, 100)
    grade = grade_for(score)

    return {
        "score": score,
        "grade": grade,
        "summary": summarize(score, grade),
        "categories": categories,
        "issues": issues,
        "word_count": word_count,
        "fix_cta": score < 80,
    }
