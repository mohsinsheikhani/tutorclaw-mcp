from __future__ import annotations

import re
from typing import Annotated, TypedDict

from pydantic import Field

from tutorclaw.store import PROJECT_ROOT, get_learner_tier

CHAPTERS_DIR = PROJECT_ROOT / "content" / "chapters"


class ChapterContentResult(TypedDict):
    learner_id: str
    chapter: int
    title: str
    section: str | None
    content: str


def _find_chapter_file(chapter: int):
    matches = list(CHAPTERS_DIR.glob(f"{chapter:02d}-*.md"))
    if not matches:
        raise ValueError(f"chapter {chapter} not found")
    return matches[0]


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)", re.MULTILINE)


def _extract_title(text: str, fallback: str) -> str:
    m = _HEADING_RE.search(text)
    return m.group(2).strip() if m else fallback


def _extract_section(text: str, section: str, chapter: int) -> tuple[str, str]:
    lines = text.splitlines(keepends=True)
    heading_re = re.compile(r"^(#{1,6})\s+(.+)")

    matched_idx = None
    matched_level = None
    matched_heading_text = None

    for i, line in enumerate(lines):
        m = heading_re.match(line)
        if m and section.lower() in m.group(2).lower():
            matched_idx = i
            matched_level = len(m.group(1))
            matched_heading_text = m.group(2).strip()
            break

    if matched_idx is None:
        raise ValueError(f"section '{section}' not found in chapter {chapter}")

    end_idx = len(lines)
    for i in range(matched_idx + 1, len(lines)):
        m = heading_re.match(lines[i])
        if m and len(m.group(1)) <= matched_level:
            end_idx = i
            break

    return matched_heading_text, "".join(lines[matched_idx:end_idx]).strip()


def get_chapter_content(
    learner_id: Annotated[
        str,
        Field(
            description="The learner's unique ID.",
            min_length=1,
        ),
    ],
    chapter: Annotated[
        int,
        Field(
            description="Chapter number to retrieve.",
            ge=1,
        ),
    ],
    section: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Optional section heading to extract (case-insensitive substring match). "
                "Returns the full chapter when omitted."
            ),
        ),
    ] = None,
) -> ChapterContentResult:
    """Retrieve markdown content for a chapter, with optional section filtering.

    Checks the learner's tier before returning content: free-tier learners can
    only access chapters 1–5. Paid-tier learners have access to all chapters.
    If a section name is provided, only that section's content is returned.
    """
    tier = get_learner_tier(learner_id)

    if tier == "free" and chapter > 5:
        raise ValueError(
            f"Chapter {chapter} requires a paid plan. "
            "Upgrade at tutorclaw.io/upgrade to unlock all chapters."
        )

    chapter_file = _find_chapter_file(chapter)
    text = chapter_file.read_text()
    title = _extract_title(text, chapter_file.stem)

    if section is not None:
        matched_heading, section_content = _extract_section(text, section, chapter)
        return {
            "learner_id": learner_id,
            "chapter": chapter,
            "title": title,
            "section": matched_heading,
            "content": section_content,
        }

    return {
        "learner_id": learner_id,
        "chapter": chapter,
        "title": title,
        "section": None,
        "content": text.strip(),
    }
