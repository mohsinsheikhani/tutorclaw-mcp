from __future__ import annotations

import pytest

from tutorclaw.tools.guidance import generate_guidance

SAMPLE_CONTENT = """\
# Chapter 1: Variables and Data Types

Variables store values so you can use them later.

## Code Examples

### Example 1: Assigning variables

```python
name = "Alice"
age = 25
print(name)
print(age)
```

**Output:**
```
Alice
25
```

### Example 2: Checking types

```python
x = 42
print(type(x))
```

**Output:**
```
<class 'int'>
```
"""

NO_CODE_CONTENT = "# Chapter with no code\n\nJust text here."


# --- stage: predict ---

def test_predict_returns_code_only():
    result = generate_guidance(stage="predict", confidence=0.5, chapter_content=SAMPLE_CONTENT)
    assert "```python" in result["content"]
    assert "Alice" in result["content"]
    assert "**Output:**" not in result["content"]


def test_predict_stage_echoed():
    result = generate_guidance(stage="predict", confidence=0.5, chapter_content=SAMPLE_CONTENT)
    assert result["stage"] == "predict"


def test_predict_system_prompt_mentions_stage():
    result = generate_guidance(stage="predict", confidence=0.5, chapter_content=SAMPLE_CONTENT)
    assert "PREDICT" in result["system_prompt_addition"]
    assert "output" in result["system_prompt_addition"].lower()


# --- stage: run ---

def test_run_returns_code_and_output():
    result = generate_guidance(stage="run", confidence=0.5, chapter_content=SAMPLE_CONTENT)
    assert "```python" in result["content"]
    assert "**Output:**" in result["content"]
    assert "Alice" in result["content"]


def test_run_system_prompt_mentions_stage():
    result = generate_guidance(stage="run", confidence=0.5, chapter_content=SAMPLE_CONTENT)
    assert "RUN" in result["system_prompt_addition"]


# --- stage: investigate ---

def test_investigate_returns_code_and_output():
    result = generate_guidance(stage="investigate", confidence=0.5, chapter_content=SAMPLE_CONTENT)
    assert "```python" in result["content"]
    assert "**Output:**" in result["content"]


def test_investigate_system_prompt_mentions_stage():
    result = generate_guidance(stage="investigate", confidence=0.5, chapter_content=SAMPLE_CONTENT)
    assert "INVESTIGATE" in result["system_prompt_addition"]


# --- confidence thresholds ---

def test_low_confidence_adds_encouraging_suffix():
    result = generate_guidance(stage="predict", confidence=0.2, chapter_content=SAMPLE_CONTENT)
    assert "encouraging" in result["system_prompt_addition"].lower()


def test_high_confidence_adds_challenge_suffix():
    result = generate_guidance(stage="predict", confidence=0.8, chapter_content=SAMPLE_CONTENT)
    assert "challenge" in result["system_prompt_addition"].lower()


def test_mid_confidence_no_extra_suffix():
    result = generate_guidance(stage="predict", confidence=0.5, chapter_content=SAMPLE_CONTENT)
    assert "encouraging" not in result["system_prompt_addition"].lower()
    assert "challenge" not in result["system_prompt_addition"].lower()


def test_confidence_boundary_low_at_zero():
    result = generate_guidance(stage="run", confidence=0.0, chapter_content=SAMPLE_CONTENT)
    assert "encouraging" in result["system_prompt_addition"].lower()


def test_confidence_boundary_exactly_0_4_is_neutral():
    result = generate_guidance(stage="run", confidence=0.4, chapter_content=SAMPLE_CONTENT)
    assert "encouraging" not in result["system_prompt_addition"].lower()
    assert "challenge" not in result["system_prompt_addition"].lower()


def test_confidence_boundary_exactly_0_7_adds_challenge():
    result = generate_guidance(stage="run", confidence=0.7, chapter_content=SAMPLE_CONTENT)
    assert "challenge" in result["system_prompt_addition"].lower()


def test_confidence_boundary_high_at_one():
    result = generate_guidance(stage="investigate", confidence=1.0, chapter_content=SAMPLE_CONTENT)
    assert "challenge" in result["system_prompt_addition"].lower()


# --- error cases ---

def test_invalid_stage_raises():
    with pytest.raises(ValueError, match="stage must be one of"):
        generate_guidance(stage="modify", confidence=0.5, chapter_content=SAMPLE_CONTENT)


def test_no_code_block_raises():
    with pytest.raises(ValueError, match="chapter content contains no code block"):
        generate_guidance(stage="predict", confidence=0.5, chapter_content=NO_CODE_CONTENT)


def test_no_code_block_run_raises():
    with pytest.raises(ValueError, match="chapter content contains no code block"):
        generate_guidance(stage="run", confidence=0.5, chapter_content=NO_CODE_CONTENT)


# --- content without output block falls back gracefully ---

def test_run_without_output_block_returns_code_only():
    content_no_output = "# Ch\n\n```python\nprint('hi')\n```\n"
    result = generate_guidance(stage="run", confidence=0.5, chapter_content=content_no_output)
    assert "```python" in result["content"]
    assert "**Output:**" not in result["content"]
