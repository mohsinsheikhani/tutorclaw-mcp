from __future__ import annotations

import json
import re
from typing import Annotated, TypedDict

from pydantic import Field

from tutorclaw.store import PROJECT_ROOT, check_tier, decrement_exchanges

CHAPTERS_DIR = PROJECT_ROOT / "content" / "chapters"
EXERCISES_DIR = PROJECT_ROOT / "content" / "exercises"


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


_MSG_PAID_PLAN = (
    "This content requires a paid plan. "
    "Call get_upgrade_url for your personal upgrade link."
)
_MSG_EXCHANGES_EXHAUSTED = (
    "You have used all 50 free exchanges for today. "
    "Call get_upgrade_url to upgrade, or try again tomorrow."
)


def _apply_free_tier_gates(tier_info: dict, chapter: int) -> None:
    """Raise ValueError if any free-tier gate blocks the request."""
    if tier_info["tier"] != "free":
        return
    if chapter > 5:
        raise ValueError(_MSG_PAID_PLAN)
    if tier_info["exchanges_remaining"] == 0:
        raise ValueError(_MSG_EXCHANGES_EXHAUSTED)


class ExerciseItem(TypedDict):
    id: str
    question: str
    hint: str
    topic: str
    difficulty: str


class ExercisesResult(TypedDict):
    learner_id: str
    chapter: int
    total: int
    filtered_by: list[str] | None
    exercises: list[ExerciseItem]


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
    """Fetch the markdown content for a chapter, optionally narrowed to a specific section.

    WHEN to call: When the learner needs to read or study chapter material, or when generate_guidance needs chapter_content as input.
    NEVER call for exercises or practice — use get_exercises to retrieve practice problems instead.
    Related: get_exercises (practice problems), generate_guidance (needs this tool's output as input).
    """
    tier_info = check_tier(learner_id)
    if "error" in tier_info:
        raise ValueError(tier_info["error"])
    _apply_free_tier_gates(tier_info, chapter)
    if tier_info["tier"] == "free":
        decrement_exchanges(learner_id)

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


def get_exercises(
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
            description="Chapter number whose exercises to retrieve.",
            ge=1,
        ),
    ],
    weak_areas: Annotated[
        list[str] | None,
        Field(
            default=None,
            description=(
                "Optional list of topic strings to filter by (case-insensitive). "
                "When omitted or empty, all exercises for the chapter are returned."
            ),
        ),
    ] = None,
) -> ExercisesResult:
    """Return practice exercises for a chapter, optionally filtered to specific topics.

    WHEN to call: When the learner is ready to practice, especially in the modify or make PRIMM-Lite stages, or when targeting weak_areas.
    NEVER call for reading material — use get_chapter_content to retrieve chapter text instead.
    Related: get_chapter_content (reading material), assess_response (evaluate exercise answers).
    """
    tier_info = check_tier(learner_id)
    if "error" in tier_info:
        raise ValueError(tier_info["error"])
    _apply_free_tier_gates(tier_info, chapter)
    if tier_info["tier"] == "free":
        decrement_exchanges(learner_id)

    exercises_file = EXERCISES_DIR / f"{chapter:02d}-exercises.json"
    if not exercises_file.exists():
        raise ValueError(f"exercises for chapter {chapter} not found")

    all_exercises: list[ExerciseItem] = json.loads(exercises_file.read_text())

    if weak_areas:
        topics = {t.lower() for t in weak_areas}
        exercises = [e for e in all_exercises if e["topic"].lower() in topics]
        filtered_by: list[str] | None = list(weak_areas)
    else:
        exercises = all_exercises
        filtered_by = None

    return {
        "learner_id": learner_id,
        "chapter": chapter,
        "total": len(exercises),
        "filtered_by": filtered_by,
        "exercises": exercises,
    }
