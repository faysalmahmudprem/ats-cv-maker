"""
Rule-based ATS *readiness* scoring engine.

Pure functions: text in, score dict out. No ML, no external APIs, no I/O.
Score six categories totalling 100 points and generate a severity-ordered
issues list with actionable fixes.

This is a heuristic readiness linter, NOT a true ATS simulator and NOT a
job-match score. True ATS ranking is always relative to a specific job
description (see ``score_cv_text(..., job_description=...)`` for the
optional JD-match supplement). The UI should label this "ATS readiness".
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Detection assets
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Phone candidates are validated by digit-count (7-15 digits), not by raw
# span length. The old pattern ``\\d[\\d\\s\\-().]{7,}\\d`` matched date
# ranges such as "2020 - 2021" as phones.
_PHONE_CANDIDATE_RE = re.compile(r"\+?[\d][\d\s\-().]{6,}[\d]")
_DATE_RANGE_INLINE_RE = re.compile(
    r"\b(?:19|20)\d{2}\s*(?:[-–—]|to)\s*(?:present|current|now|(?:19|20)\d{2})\b",
    re.IGNORECASE,
)
_MONTH_RANGE_RE = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+"
    r"(?:19|20)\d{2}\s*(?:[-–—]|to|until)\s*"
    r"(?:present|current|now|(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+)?(?:19|20)\d{2})",
    re.IGNORECASE,
)
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")

# Quantification: percentages, money, scale (200+, 3x) and counts with
# explicit impact nouns ("team of 3", "500 users", "12 features").
QUANT_RE = re.compile(
    r"\d+\s?%"
    r"|\$\s?\d[\d,.\s]*[kKmM]?\b"
    r"|\b\d+\+"
    r"|\b\d+\s?x\b"
    r"|\bteam\s+of\s+\d+"
    r"|\b\d+\s?(users?|clients?|customers?|projects?|features?|people|members?|"
    r"developers?|engineers?|requests?|sales|years?|months?|reports?)\b",
    re.IGNORECASE,
)

ACTION_VERBS = [
    # Core (original list, kept for backwards compatibility).
    "led", "built", "developed", "managed", "created", "designed",
    "implemented", "improved", "increased", "reduced", "achieved",
    "delivered", "launched", "coordinated", "optimized",
    # Extended industry-standard achievement verbs.
    "accelerated", "administered", "advised", "allocated", "analyzed",
    "approved", "architected", "assessed", "audited", "automated",
    "boosted", "budgeted", "championed", "collaborated", "completed",
    "consolidated", "constructed", "consulted", "cut", "debugged",
    "decreased", "defined", "delegated", "demonstrated", "deployed",
    "detected", "directed", "documented", "doubled", "drove",
    "earned", "edited", "enabled", "engineered", "established",
    "evaluated", "exceeded", "executed", "expanded", "expedited",
    "founded", "formulated", "generated", "grew", "guided",
    "halved", "headed", "hired", "identified", "initiated",
    "inspected", "installed", "instituted", "instructed", "integrated",
    "interpreted", "introduced", "invented", "maintained", "mapped",
    "marketed", "mentored", "merged", "migrated", "moderated",
    "monitored", "negotiated", "operated", "orchestrated", "organized",
    "overhauled", "oversaw", "partnered", "performed", "piloted",
    "pioneered", "planned", "prepared", "presented", "prevented",
    "prioritized", "processed", "produced", "programmed", "projected",
    "promoted", "proposed", "published", "purchased", "raised",
    "ranked", "ratified", "rebuilt", "recruited", "refactored",
    "remodeled", "reorganized", "repaired", "reported", "researched",
    "resolved", "restructured", "revamped", "reviewed", "revitalized",
    "saved", "scheduled", "secured", "shipped", "simplified",
    "solved", "sourced", "spearheaded", "specified", "started",
    "streamlined", "strengthened", "supervised", "supported", "surpassed",
    "tested", "trained", "transformed", "tripled", "upgraded",
    "validated", "visualized", "wrote",
]

TECH_KEYWORDS = [
    # Software / IT (original list, kept).
    "javascript", "python", "php", "react", "laravel", "django", "mysql",
    "postgresql", "api", "rest", "git", "docker", "aws", "linux",
    "typescript", "node", "sql",
    # Cross-industry professional skills: finance, healthcare, education,
    # marketing, operations, trades. Without these, non-engineering CVs
    # always failed the "technical skills" check.
    "excel", "accounting", "bookkeeping", "auditing", "budgeting",
    "financial", "marketing", "sales", "seo", "crm", "negotiation",
    "nursing", "patient", "clinical", "pharmacy", "caregiving",
    "teaching", "curriculum", "training", "research", "laboratory",
    "engineering", "autocad", "welding", "machining", "electrician",
    "plumbing", "driving", "logistics", "warehouse", "procurement",
    "photoshop", "illustrator", "design", "writing", "editing",
    "customer service", "data entry",
]

SOFT_SKILLS = [
    "team", "teamwork", "communication", "leadership", "collaboration",
    "problem", "problem-solving", "analytical", "stakeholder",
    "cross-functional", "adaptability", "time management",
]

# Full box-drawing / block set. The old 3-char list missed ─ └ ┘ etc.
BOX_CHARS = [
    "│", "┌", "╔", "─", "━", "┃", "└", "┘", "┐", "┌",
    "├", "┤", "┬", "┴", "┼", "╚", "╝", "╠", "╣", "╦", "╩",
    "█", "▓", "▒", "░",
]

# True bullet glyphs. Hyphen/dash variants are handled separately in
# _count_bullets() so date ranges ("2020 - 2021") are not miscounted.
BULLET_GLYPHS = ["•", "▪", "·", "‣", "◦", "●", "○", "∙", "*"]

# Section heading aliases (singular + plural + common variants).
HEADING_ALIASES: Dict[str, List[str]] = {
    "experience": ["experience", "employment", "work history", "professional experience"],
    "education": ["education", "academic background", "academic qualifications"],
    "skills": ["skills", "skill", "technical skills", "competencies", "core competencies"],
    "summary": ["summary", "objective", "profile", "career objective", "professional summary", "about me"],
    "projects": ["projects", "project", "selected projects", "personal projects"],
    "certifications": ["certifications", "certification", "certificates", "certificate", "licenses", "licences"],
}

SECTION_HEADINGS = [
    "experience", "education", "skills", "summary", "objective",
    "projects", "certifications",
]

COMMON_MISSPELLINGS = [
    "recieve", "seperate", "managment", "experiance", "acheived",
    "sucessful", "occured", "neccessary", "writting", "comming",
    "maintainance", "tommorrow", "definately", "calender",
]

BUZZWORDS_WITHOUT_EVIDENCE = [
    "hard worker", "hard-worker", "team player", "detail-oriented",
    "detail oriented", "results-driven", "results driven", "go-getter",
    "go getter", "think outside the box",
]

PERSONAL_PRONOUNS_RE = re.compile(r"\b(I|me|my|mine|myself)\b")

_STOPWORDS = frozenset(
    "a an the and or of to in for on with as at by from is are was were be been "
    "this that these those it its we you your our ours their his her him she he "
    "will would can could should shall may might must do does did done have has had "
    "not no yes if then than so such very just about into over after before between "
    "role looking seeking join including plus".split()
)


# ---------------------------------------------------------------------------
# Word-boundary helpers (fix substring false positives)
# ---------------------------------------------------------------------------

def _word_in(haystack_lower: str, phrase: str) -> bool:
    """Case-insensitive whole-word/phrase match.

    ``"led" in "skilled"`` is True with ``in`` but must NOT count as the
    action verb "led". Likewise ``"api"`` must not match ``"rapid"`` and
    ``"design"`` must not match ``"designed"``.
    """
    return bool(re.search(r"\b" + re.escape(phrase.lower()) + r"\b", haystack_lower))


def _has_phone(text: str) -> bool:
    """Phone detection by digit-count, ignoring date ranges.

    A candidate must contain 7-15 digits. Date ranges such as
    "2020 - 2021" or "Jan 2022 - Present" are stripped first so they can
    never satisfy the phone check.
    """
    scrubbed = _DATE_RANGE_INLINE_RE.sub(" ", text)
    scrubbed = _MONTH_RANGE_RE.sub(" ", scrubbed)
    for match in _PHONE_CANDIDATE_RE.finditer(scrubbed):
        digits = re.sub(r"\D", "", match.group(0))
        if 7 <= len(digits) <= 15:
            # A bare 4-digit year (possibly with parens) is not a phone.
            if len(digits) == 4 and match.group(0).strip(" ().-") == digits:
                continue
            return True
    return False


def _has_linkedin(text: str) -> bool:
    return bool(re.search(r"linkedin\.com/in/\S", text.lower())) or "linkedin.com" in text.lower()


def _date_ranges(text: str) -> List[str]:
    found = _MONTH_RANGE_RE.findall(text)
    # findall on a pattern with groups returns tuples; fall back to finditer.
    if found and isinstance(found[0], tuple):
        return [m.group(0) for m in _MONTH_RANGE_RE.finditer(text)] + [
            m.group(0) for m in _DATE_RANGE_INLINE_RE.finditer(text)
        ]
    return list(found) + _DATE_RANGE_INLINE_RE.findall(text)


def _count_bullets(text: str) -> int:
    """Count bullet lines without mistaking hyphens/date ranges."""
    count = 0
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line[0] in BULLET_GLYPHS:
            # Require real content after the marker ("• " + 2+ chars).
            if len(line) >= 3:
                count += 1
            continue
        if line[0] in ("-", "–", "—"):
            rest = line[1:].strip()
            if len(rest) < 2:
                continue
            # Reject date-like lines: "- 2021", "- Present", "2020 - 2021".
            if re.match(r"^(\(?(19|20)\d{2}\)?|present|current|now)\b", rest, re.IGNORECASE):
                continue
            if re.match(r"^(19|20)\d{2}\s*[-–—]", line):
                continue
            # Hyphen bullets need a space after the dash ("- Led ...").
            if raw_line.lstrip()[1:2] == " " or line[1:2] == " ":
                count += 1
    return count


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]*", text.lower())


# ---------------------------------------------------------------------------
# Category scorers — each returns (points_awarded, max_points, failed_checks)
# where failed_checks is a list of (severity, title, detail, fix) tuples.
# ---------------------------------------------------------------------------


def _score_format(text: str) -> tuple[int, int, List[tuple[str, str, str, str]]]:
    max_pts = 20
    score = max_pts
    issues: List[tuple[str, str, str, str]] = []

    has_box_chars = any(ch in text for ch in BOX_CHARS)
    stripped = text.strip()
    first_100 = stripped[:100]
    no_alnum_start = bool(stripped) and not any(c.isalnum() for c in first_100)
    word_count = len(text.split())

    if has_box_chars:
        score -= 10
        issues.append((
            "high",
            "Complex formatting detected",
            "Your CV contains table or box-drawing characters that ATS parsers cannot read.",
            "Remove tables and text boxes — use a single-column layout",
        ))
    if no_alnum_start:
        score -= 5
        issues.append((
            "medium",
            "Unusual document start",
            "The first 100 characters contain no readable text — parsers may misread headers or images.",
            "Start with your name and contact details as plain text",
        ))
    if word_count < 100:
        score -= 5
    if 0 < word_count < 50:
        issues.append((
            "high",
            "Very little extractable text",
            f"Only {word_count} words could be read — the file may be scanned or image-based.",
            "Export as real text (Word/PDF with selectable text), not scanned images",
        ))

    lower = text.lower()
    misspellings = sorted({w for w in COMMON_MISSPELLINGS if _word_in(lower, w)})
    if misspellings:
        issues.append((
            "low",
            "Possible spelling errors",
            f"Found: {', '.join(misspellings[:5])}. ATS and recruiters penalize typos.",
            "Proofread or run a spellchecker over the full CV",
        ))
    if PERSONAL_PRONOUNS_RE.search(text):
        issues.append((
            "low",
            "Personal pronouns detected",
            "First-person pronouns (I/me/my) are non-standard in CVs.",
            "Remove 'I/me/my' — start bullets with verbs instead",
        ))

    return max(score, 0), max_pts, issues


def _score_contact(text: str) -> tuple[int, int, List[tuple[str, str, str, str]]]:
    max_pts = 15
    score = 0
    issues: List[tuple[str, str, str, str]] = []

    has_email = bool(EMAIL_RE.search(text))
    has_phone = _has_phone(text)
    has_linkedin = _has_linkedin(text)

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

    # Informational only (no points): location helps recruiters filter.
    if not re.search(r"\b(dhaka|bangladesh|remote|[A-Z][a-z]+,\s*[A-Z][a-z]+)\b", text):
        issues.append((
            "low",
            "Location unclear",
            "No city/country or Remote marker was detected.",
            "Add 'City, Country' or 'Remote' to your contact line",
        ))

    return score, max_pts, issues


def _score_keywords(text: str) -> tuple[int, int, List[tuple[str, str, str, str]]]:
    max_pts = 25
    score = 0
    issues: List[tuple[str, str, str, str]] = []
    lower = text.lower()

    action_hits = sum(1 for verb in ACTION_VERBS if _word_in(lower, verb))
    if action_hits > 0:
        score += 5
    else:
        issues.append((
            "high",
            "No achievement language detected",
            "Bullet points read as duties rather than achievements.",
            "Start bullet points with action verbs: Led, Built, Increased, Reduced",
        ))

    tech_hits = sum(1 for kw in TECH_KEYWORDS if _word_in(lower, kw))
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

    if any(_word_in(lower, sk) for sk in SOFT_SKILLS):
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

    # Keyword stuffing guard (informational, no deduction to stay stable).
    words = len(text.split())
    if words and tech_hits / max(words, 1) > 0.15 and words < 200:
        issues.append((
            "low",
            "Possible keyword stuffing",
            "Very high keyword density in a short document can look spammy.",
            "Keep keywords in context — one Skills section plus natural use",
        ))

    buzz = [b for b in BUZZWORDS_WITHOUT_EVIDENCE if b in lower]
    if buzz and not QUANT_RE.search(text):
        issues.append((
            "low",
            "Buzzwords without evidence",
            f"Found '{buzz[0]}' with no numbers to back it up.",
            "Pair claims with proof: numbers, scope, or outcomes",
        ))

    return score, max_pts, issues


def _score_experience(text: str) -> tuple[int, int, List[tuple[str, str, str, str]]]:
    max_pts = 20
    score = 0
    issues: List[tuple[str, str, str, str]] = []
    lower = text.lower()

    if any(
        _word_in(lower, h) if " " not in h else h in lower
        for h in ("experience", "employment", "work history")
    ):
        score += 5
    else:
        issues.append((
            "medium",
            "Experience section unclear",
            "No Experience/Employment heading was found.",
            "Add a clearly labelled 'Professional Experience' section",
        ))

    ranges = _date_ranges(text)
    year_count = len(YEAR_RE.findall(text))
    if ranges:
        score += 10
    elif year_count >= 2:
        # Legacy behaviour gave full marks for any 2 years; now partial —
        # isolated years without ranges are ambiguous timelines.
        score += 5
        issues.append((
            "medium",
            "Work dates unclear",
            "Year mentions found but no clear date ranges (e.g. 'Jan 2022 – Present').",
            "Add clear date ranges: 'Jan 2022 – Present'",
        ))
    else:
        issues.append((
            "medium",
            "Work dates unclear",
            "Fewer than two year references were found, so timelines are ambiguous.",
            "Add clear date ranges: 'Jan 2022 – Present'",
        ))

    bullet_lines = _count_bullets(text)
    if bullet_lines >= 3:
        score += 5
    else:
        issues.append((
            "medium",
            "Missing achievement bullets",
            f"Only {bullet_lines} bullet-style line(s) detected — at least 3 expected.",
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
    for canonical, aliases in HEADING_ALIASES.items():
        if canonical == "summary":
            continue  # counted once below (summary/objective share a slot)
        if any(_word_in(lower, a) if " " not in a else a in lower for a in aliases):
            found += 1
    if any(_word_in(lower, a) if " " not in a else a in lower for a in HEADING_ALIASES["summary"]):
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
# Job-description match (supplement — does NOT change the 0-100 total)
# ---------------------------------------------------------------------------

def match_job_description(cv_text: str, jd_text: str, top_n: int = 20) -> Dict[str, Any]:
    """Score CV against a specific job description.

    Industry-standard ATS ranking is relative to a posting. This returns a
    0-100 keyword-overlap score plus matched/missing keyword lists. It is
    deliberately separate from the absolute readiness total so the existing
    0-100 contract stays stable.
    """
    cv_tokens = {t for t in _tokenize(cv_text) if len(t) >= 3 and t not in _STOPWORDS}
    jd_tokens = [t for t in _tokenize(jd_text) if len(t) >= 3 and t not in _STOPWORDS]
    # Preserve JD frequency order, deduplicate.
    seen: Dict[str, None] = {}
    for tok in jd_tokens:
        seen.setdefault(tok)
    jd_unique = list(seen.keys())

    if not jd_unique:
        return {"score": 0, "matched": [], "missing": [], "jd_keywords": 0}

    matched = [t for t in jd_unique if t in cv_tokens]
    missing = [t for t in jd_unique if t not in cv_tokens]
    score = round(100 * len(matched) / len(jd_unique)) if jd_unique else 0
    return {
        "score": score,
        "matched": matched[:top_n],
        "missing": missing[:top_n],
        "jd_keywords": len(jd_unique),
    }


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
    """A >= 85, B >= 70, C >= 55, D >= 40, else F.

    Calibrated so 80+ (fix_cta cut-off) means "strong readiness";
    A is reserved for near-perfect parses.
    """
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


def score_cv_text(text: str, job_description: Optional[str] = None) -> Dict[str, Any]:
    """Score extracted CV text and return the full score dict.

    ``job_description`` is optional: when supplied, a ``jd_match`` supplement
    (0-100 JD keyword overlap + missing keywords) is included without
    changing the absolute 0-100 readiness total.
    """
    word_count = len(text.split())

    # An empty extraction has nothing to score: the literal format rules
    # would still award points (no box chars, no content to offend), which
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

    out: Dict[str, Any] = {
        "score": score,
        "grade": grade,
        "summary": summarize(score, grade),
        "categories": categories,
        "issues": issues,
        "word_count": word_count,
        "fix_cta": score < 80,
    }
    if job_description:
        out["jd_match"] = match_job_description(text, job_description)
    return out
