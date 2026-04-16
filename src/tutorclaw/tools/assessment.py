from __future__ import annotations

from typing import Annotated, TypedDict

from pydantic import Field

from tutorclaw.store import check_tier, decrement_exchanges

_MSG_EXCHANGES_EXHAUSTED = (
    "You have used all 50 free exchanges for today. "
    "Call get_upgrade_url to upgrade, or try again tomorrow."
)

_VALID_STAGES = ("predict", "run", "investigate")

_VAGUE_PHRASES = frozenset(
    {
        "i don't know",
        "i dont know",
        "idk",
        "stuff",
        "things",
        "it does stuff",
    }
)

_RECOMMENDATIONS: dict[str, dict[str, str]] = {
    "predict": {
        "strong": "Advance to the run stage.",
        "partial": "Stay in predict and revisit the prediction.",
        "weak": "Stay in predict with a simpler example.",
    },
    "run": {
        "strong": "Advance to the investigate stage.",
        "partial": "Revisit the prediction before advancing.",
        "weak": "Stay in run and review the output together.",
    },
    "investigate": {
        "strong": "Move to the next chapter or a harder example.",
        "partial": "Stay in investigate and explore a modification.",
        "weak": "Stay in investigate and explore a modification.",
    },
}


class AssessmentResult(TypedDict):
    confidence_delta: float
    feedback: str
    recommendation: str


def _is_vague(text: str) -> bool:
    stripped = text.strip().lower()
    if len(stripped) < 10:
        return True
    return stripped in _VAGUE_PHRASES


def _match_concepts(answer: str, concepts: list[str]) -> tuple[list[str], list[str]]:
    lower = answer.lower()
    matched = [c for c in concepts if c.lower() in lower]
    unmatched = [c for c in concepts if c.lower() not in lower]
    return matched, unmatched


def _strength(ratio: float, vague: bool) -> str:
    if vague:
        return "weak"
    if ratio >= 0.8:
        return "strong"
    if ratio >= 0.3:
        return "partial"
    return "weak"


def _delta(strength: str) -> float:
    return {"strong": 0.2, "partial": 0.1, "weak": -0.1}.get(strength, -0.1)


def _build_feedback(
    strength: str,
    matched: list[str],
    unmatched: list[str],
    all_concepts: list[str],
) -> str:
    if strength == "strong":
        return f"Good answer! You demonstrated understanding of: {', '.join(matched)}."
    if strength == "partial":
        matched_str = ", ".join(matched) if matched else "none of the key concepts"
        unmatched_str = ", ".join(unmatched)
        return f"You covered {matched_str}. Focus next on: {unmatched_str}."
    # weak
    concepts_str = ", ".join(all_concepts)
    first = all_concepts[0]
    return (
        f"Your answer didn't address the key concepts: {concepts_str}. "
        f"Think about what {first} means here."
    )


def assess_response(
    learner_id: Annotated[
        str,
        Field(
            description="The learner's unique ID.",
            min_length=1,
        ),
    ],
    answer_text: Annotated[
        str,
        Field(
            description="The learner's answer text.",
            min_length=1,
        ),
    ],
    primm_stage: Annotated[
        str,
        Field(
            description="The learner's current PRIMM-Lite stage: predict, run, or investigate.",
        ),
    ],
    expected_concepts: Annotated[
        list[str],
        Field(
            description=(
                "Concepts the answer should demonstrate understanding of. "
                "Checked via case-insensitive substring match against the answer text."
            ),
            min_length=1,
        ),
    ],
) -> AssessmentResult:
    """Score a learner's answer against expected concepts and return a confidence adjustment, feedback, and next-step recommendation.

    WHEN to call: When a learner submits a natural-language answer to a predict, run, or investigate prompt and you need to evaluate their understanding.
    NEVER call for general conversation — only use when the learner is answering a PRIMM-Lite stage question. Use submit_code for code submissions.
    Related: submit_code (execute code, not text answers), update_progress (apply the returned confidence_delta and recommendation).
    """
    tier_info = check_tier(learner_id)
    if "error" in tier_info:
        raise ValueError(tier_info["error"])
    if tier_info["tier"] == "free":
        if tier_info["exchanges_remaining"] == 0:
            raise ValueError(_MSG_EXCHANGES_EXHAUSTED)
        decrement_exchanges(learner_id)

    if primm_stage not in _VALID_STAGES:
        raise ValueError(f"stage must be one of: {', '.join(_VALID_STAGES)}")
    if not expected_concepts:
        raise ValueError("expected_concepts must not be empty")

    vague = _is_vague(answer_text)
    matched, unmatched = _match_concepts(answer_text, expected_concepts)
    ratio = len(matched) / len(expected_concepts)

    strength = _strength(ratio, vague)
    delta = -0.2 if vague else _delta(strength)
    feedback = _build_feedback(strength, matched, unmatched, expected_concepts)
    recommendation = _RECOMMENDATIONS[primm_stage][strength]

    return {
        "confidence_delta": delta,
        "feedback": feedback,
        "recommendation": recommendation,
    }
