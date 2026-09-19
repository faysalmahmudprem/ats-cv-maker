"""Pydantic schemas for the CV generation API.

These models define the request contract for POST /api/generate-cv.
They mirror the data structure of the original generator:
name / professional_title / contact / summary / skills / experience /
projects / education / certifications / additional_info (+ languages).

All string fields are stripped automatically and length-capped so that
a single user request can never produce an absurd document.
"""

from __future__ import annotations

import re
from typing import Annotated, List, Union

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.profiles import PROFILES
from app.templates import TEMPLATES

# Same relaxed email rule the frontend uses: something@something.tld
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ---- Shared constrained string types (beginner-readable aliases) ----
ShortText = str  # alias kept for readability in comments below


class CVBaseModel(BaseModel):
    """Base model: strips whitespace, ignores unknown extra fields."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


# ---- Contact ----


class LinkDetail(CVBaseModel):
    """Optional richer form of a contact link: {"text": ..., "url": ...}."""

    text: str = Field(default="", max_length=120)
    url: str = Field(default="", max_length=300)


# A contact link can arrive as a plain string or as {text, url}.
# The plain-string branch is capped so an oversized value is rejected by
# validation instead of reaching the generated document.
CappedLink = Annotated[str, StringConstraints(max_length=300)]
ContactLink = Union[CappedLink, LinkDetail]


class Contact(CVBaseModel):
    location: str = Field(default="", max_length=80)
    phone: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=120)
    linkedin: ContactLink = ""
    github: ContactLink = ""
    portfolio: ContactLink = ""

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        if value and not EMAIL_RE.match(value):
            raise ValueError("must be a valid email address (e.g. name@example.com)")
        return value


# ---- Skills ----


class SkillGroup(CVBaseModel):
    category: str = Field(default="", max_length=60)
    items: List[str] = Field(default_factory=list, max_length=40)

    @field_validator("items", mode="before")
    @classmethod
    def split_comma_string(cls, value: object) -> object:
        """Accept "PHP, React" as well as ["PHP", "React"]."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("items")
    @classmethod
    def clean_items(cls, items: List[str]) -> List[str]:
        return [item.strip()[:60] for item in items if item.strip()]


# ---- Experience / Projects / Education ----


class Experience(CVBaseModel):
    title: str = Field(default="", max_length=80)
    company: str = Field(default="", max_length=80)
    location: str = Field(default="", max_length=80)
    dates: str = Field(default="", max_length=60)
    bullets: List[str] = Field(default_factory=list, max_length=15)

    @field_validator("bullets")
    @classmethod
    def clean_bullets(cls, bullets: List[str]) -> List[str]:
        return [b.strip()[:300] for b in bullets if b.strip()]


class Project(CVBaseModel):
    name: str = Field(default="", max_length=80)
    technologies: List[str] = Field(default_factory=list, max_length=20)
    description: str = Field(default="", max_length=600)
    details: List[str] = Field(default_factory=list, max_length=10)

    @field_validator("technologies", mode="before")
    @classmethod
    def split_comma_string(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("details")
    @classmethod
    def clean_details(cls, details: List[str]) -> List[str]:
        return [d.strip()[:300] for d in details if d.strip()]


class Education(CVBaseModel):
    degree: str = Field(default="", max_length=100)
    school: str = Field(default="", max_length=100)
    location: str = Field(default="", max_length=80)
    dates: str = Field(default="", max_length=60)
    details: List[str] = Field(default_factory=list, max_length=10)

    @field_validator("details")
    @classmethod
    def clean_details(cls, details: List[str]) -> List[str]:
        return [d.strip()[:300] for d in details if d.strip()]


# ---- Certifications / Languages / Extra lines ----


class Certification(CVBaseModel):
    title: str = Field(default="", max_length=120)
    issuer: str = Field(default="", max_length=80)
    date: str = Field(default="", max_length=40)


class CVRequest(CVBaseModel):
    """The full request body for POST /api/generate-cv."""

    # Template choice is validated against the registry at import time,
    # so adding a template in app/templates.py needs no schema change.
    template: str = Field(default="classic")
    # Output format: "docx" (default) or "pdf". Same CV, same layout,
    # different file type.
    format: str = Field(default="docx")
    # Profile controls document STRUCTURE (section order + headings):
    # "experienced" (default) or "fresher" (education/projects first,
    # experience optional). See app/profiles.py.
    profile: str = Field(default="experienced")
    name: str = Field(min_length=1, max_length=80)
    professional_title: str = Field(default="", max_length=80)
    contact: Contact = Field(default_factory=Contact)
    summary: str = Field(default="", max_length=1200)
    skills: List[SkillGroup] = Field(default_factory=list, max_length=25)
    experience: List[Experience] = Field(default_factory=list, max_length=15)
    projects: List[Project] = Field(default_factory=list, max_length=10)
    education: List[Education] = Field(default_factory=list, max_length=10)
    certifications: List[Certification] = Field(default_factory=list, max_length=15)
    languages: List[str] = Field(default_factory=list, max_length=10)
    additional_info: List[str] = Field(default_factory=list, max_length=10)

    @field_validator("format")
    @classmethod
    def known_format(cls, value: str) -> str:
        allowed = ("docx", "pdf")
        if value not in allowed:
            raise ValueError(f"unknown format '{value}'. Valid options: {', '.join(allowed)}")
        return value

    @field_validator("template")
    @classmethod
    def known_template(cls, value: str) -> str:
        if value not in TEMPLATES:
            allowed = ", ".join(sorted(TEMPLATES))
            raise ValueError(f"unknown template '{value}'. Valid options: {allowed}")
        return value

    @field_validator("profile")
    @classmethod
    def known_profile(cls, value: str) -> str:
        if value not in PROFILES:
            allowed = ", ".join(sorted(PROFILES))
            raise ValueError(f"unknown profile '{value}'. Valid options: {allowed}")
        return value

    @field_validator("languages")
    @classmethod
    def clean_languages(cls, languages: List[str]) -> List[str]:
        return [lang.strip()[:60] for lang in languages if lang.strip()]

    @field_validator("additional_info")
    @classmethod
    def clean_additional(cls, lines: List[str]) -> List[str]:
        return [line.strip()[:300] for line in lines if line.strip()]

    @model_validator(mode="after")
    def drop_empty_entries(self) -> "CVRequest":
        """Ignore list entries where every field is blank (defensive,
        mirrors what the old frontend filtered out client-side)."""
        self.experience = [e for e in self.experience if e.title or e.company or e.bullets]
        self.education = [e for e in self.education if e.degree or e.school or e.details]
        self.projects = [p for p in self.projects if p.name or p.description or p.details]
        self.certifications = [c for c in self.certifications if c.title or c.issuer]
        self.skills = [s for s in self.skills if s.items]
        return self
