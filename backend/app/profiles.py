"""CV profile registry: Experienced vs Fresher/Entry-level.

A profile changes document STRUCTURE — section order and headings —
not presentation (that is what templates do). Combined with a
TemplateStyle it fully determines the generated document.

Validation semantics per profile live in the schemas (projects required,
experience optional in fresher mode) and are mirrored in the frontend.

Requirement enforcement (e.g. "projects required, experience optional"
for freshers) is intentionally a FRONTEND concern, exactly like the
existing "experience required" rule for the experienced profile — the
API itself stays lenient so edge users are never locked out.

To add a profile: add one Profile entry to PROFILES. The schema validator
and this module's get_profile() pick it up automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Profile:
    key: str
    label: str  # shown in the UI toggle
    # Section keys in DOCX order. Each maps to a builder in the generator;
    # unknown keys are skipped so the list stays safe to edit.
    section_order: tuple[str, ...]
    # Per-profile heading overrides (section key -> heading text).
    headings: dict[str, str] = field(default_factory=dict)


PROFILES: dict[str, Profile] = {
    "experienced": Profile(
        key="experienced",
        label="Experienced",
        section_order=(
            "summary",
            "skills",
            "experience",
            "projects",
            "education",
            "certifications",
            "languages",
            "additional_info",
        ),
    ),
    "fresher": Profile(
        key="fresher",
        label="Fresher / Entry-level",
        # Education and projects lead; internships/experience is optional
        # and comes after skills. Summary uses the Career Objective heading.
        section_order=(
            "summary",
            "education",
            "projects",
            "skills",
            "experience",
            "certifications",
            "languages",
            "additional_info",
        ),
        headings={"summary": "Career Objective", "experience": "Internships / Part-time Work"},
    ),
}

DEFAULT_PROFILE = "experienced"


def get_profile(key: str | None) -> Profile:
    """Resolve a profile key, falling back to the default."""
    if key and key in PROFILES:
        return PROFILES[key]
    return PROFILES[DEFAULT_PROFILE]


def section_heading(profile: Profile, section: str, default: str) -> str:
    """Heading text for a section under the given profile."""
    return profile.headings.get(section, default)
