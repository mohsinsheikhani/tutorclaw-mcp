from __future__ import annotations

import re
from typing import Annotated, TypedDict

from pydantic import Field

_VALID_STAGES = ("predict", "run", "investigate")

_STAGE_INSTRUCTIONS: dict[str, str] = {
    "predict": (
        "The learner is in the PREDICT stage. "
        "Present the code block above and ask what they think it will output. "
        "Do not reveal the output. Wait for their answer before proceeding."
    ),
    "run": (
        "The learner is in the RUN stage. "
        "Show the code and its actual output. "
        "Ask whether the output matched their prediction. "
        "If not, invite them to guess why."
    ),
    "investigate": (
        "The learner is in the INVESTIGATE stage. "
        "Ask them to explain why the output is what it is, "
        "or what would change if they modified one line of the code. "
        "Encourage thinking out loud."
    ),
}


class GuidanceResult(TypedDict):
    stage: str
    content: str
    system_prompt_addition: str


def _extract_first_code_block(text: str) -> str:
    m = re.search(r"(```python\n.*?```)", text, re.DOTALL)
    if not m:
        raise ValueError("chapter content contains no code block")
    return m.group(1)


def _extract_code_with_output(text: str) -> str:
    code_m = re.search(r"(```python\n.*?```)", text, re.DOTALL)
    if not code_m:
        raise ValueError("chapter content contains no code block")
    rest = text[code_m.end():]
    output_m = re.search(r"(\*\*Output:\*\*\s*```\n.*?```)", rest, re.DOTALL)
    if output_m:
        return code_m.group(1) + "\n\n" + output_m.group(1)
    return code_m.group(1)


def _confidence_suffix(confidence: float) -> str:
    if confidence < 0.4:
        return " Be encouraging and guide them with hints if they struggle."
    if confidence >= 0.7:
        return " Challenge them with a follow-up question if they answer correctly."
    return ""


def generate_guidance(
    stage: Annotated[
        str,
        Field(
            description="The learner's current PRIMM-Lite stage: predict, run, or investigate.",
        ),
    ],
    confidence: Annotated[
        float,
        Field(
            description="The learner's current confidence score (0.0–1.0).",
            ge=0.0,
            le=1.0,
        ),
    ],
    chapter_content: Annotated[
        str,
        Field(
            description="Raw markdown content for the current chapter.",
            min_length=1,
        ),
    ],
) -> GuidanceResult:
    """Generate stage-appropriate content and agent behavioral instructions for the PRIMM-Lite teaching loop.

    Returns the content to show the learner and a system_prompt_addition that tells the
    agent how to behave this turn. The agent must follow system_prompt_addition exactly.
    Confidence adjusts the tone: low confidence (< 0.4) gets supportive guidance,
    high confidence (>= 0.7) gets an additional challenge.
    """
    if stage not in _VALID_STAGES:
        raise ValueError(f"stage must be one of: {', '.join(_VALID_STAGES)}")

    if stage == "predict":
        content = _extract_first_code_block(chapter_content)
    else:
        content = _extract_code_with_output(chapter_content)

    system_prompt_addition = _STAGE_INSTRUCTIONS[stage] + _confidence_suffix(confidence)

    return {
        "stage": stage,
        "content": content,
        "system_prompt_addition": system_prompt_addition,
    }
