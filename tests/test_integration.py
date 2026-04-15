from __future__ import annotations

import asyncio
import subprocess
import sys
import time

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from tutorclaw import store
from tutorclaw.store import MOCK_API_KEY, MOCK_LEARNER_ID

URL = "http://127.0.0.1:8000/mcp"


@pytest.fixture(scope="module")
def server():
    # Clean slate before the server starts
    store.reset()

    proc = subprocess.Popen(
        [sys.executable, "-m", "tutorclaw"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    deadline = time.time() + 10
    ready = False
    while time.time() < deadline:
        try:
            httpx.get(URL, timeout=0.5)
            ready = True
            break
        except Exception:
            time.sleep(0.2)
    if not ready:
        proc.terminate()
        raise RuntimeError("server failed to start")

    yield URL

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    # Clean up persisted data
    store.reset()


async def _call(url: str, tool: str = "register_learner", **kwargs):
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert any(t.name == tool for t in tools.tools)
            return await session.call_tool(tool, kwargs)


def test_register_via_http(server):
    result = asyncio.run(_call(server, name="Ada"))
    assert not result.isError
    payload = result.structuredContent
    assert payload["name"] == "Ada"
    assert payload["learner_id"] == MOCK_LEARNER_ID
    assert payload["email"] is None
    assert payload["tier"] == "free"
    assert payload["api_key"] == MOCK_API_KEY
    assert "Ada" in payload["welcome_message"]


def test_register_with_email_via_http(server):
    result = asyncio.run(_call(server, name="Grace", email="grace@example.com"))
    assert not result.isError
    # Mock ID already exists from previous test, so original record is returned
    payload = result.structuredContent
    assert payload["learner_id"] == MOCK_LEARNER_ID


def test_invalid_email_via_http(server):
    result = asyncio.run(_call(server, name="Bad", email="not-an-email"))
    assert result.isError
    assert "valid address" in result.content[0].text


def test_get_learner_state_via_http(server):
    # Ensure learner exists (may already from prior test)
    asyncio.run(_call(server, tool="register_learner", name="Ada"))
    result = asyncio.run(_call(server, tool="get_learner_state", learner_id=MOCK_LEARNER_ID))
    assert not result.isError
    payload = result.structuredContent
    assert payload["learner_id"] == MOCK_LEARNER_ID
    assert payload["chapter"] == 1
    assert payload["stage"] == "predict"
    assert payload["confidence"] == 0.5
    assert payload["tier"] == "free"
    assert payload["exchanges_remaining"] == 50
    assert payload["weak_areas"] == []


def test_get_learner_state_not_found_via_http(server):
    result = asyncio.run(_call(server, tool="get_learner_state", learner_id="nonexistent"))
    assert result.isError
    assert "learner not found" in result.content[0].text


def test_update_progress_via_http(server):
    # Ensure learner exists
    asyncio.run(_call(server, tool="register_learner", name="Ada"))
    result = asyncio.run(
        _call(
            server,
            tool="update_progress",
            learner_id=MOCK_LEARNER_ID,
            chapter=2,
            stage="run",
            confidence_delta=0.1,
        )
    )
    assert not result.isError
    payload = result.structuredContent
    assert payload["chapter"] == 2
    assert payload["stage"] == "run"
    assert payload["confidence"] == pytest.approx(0.6)
    assert payload["tier"] == "free"


def test_update_progress_invalid_stage_via_http(server):
    asyncio.run(_call(server, tool="register_learner", name="Ada"))
    result = asyncio.run(
        _call(
            server,
            tool="update_progress",
            learner_id=MOCK_LEARNER_ID,
            chapter=1,
            stage="invalid",
            confidence_delta=0.0,
        )
    )
    assert result.isError
    assert "stage must be one of" in result.content[0].text


def test_update_progress_learner_not_found_via_http(server):
    result = asyncio.run(
        _call(
            server,
            tool="update_progress",
            learner_id="nonexistent",
            chapter=1,
            stage="predict",
            confidence_delta=0.0,
        )
    )
    assert result.isError
    assert "learner not found" in result.content[0].text


def test_get_chapter_content_full_via_http(server):
    asyncio.run(_call(server, tool="register_learner", name="Ada"))
    result = asyncio.run(
        _call(server, tool="get_chapter_content", learner_id=MOCK_LEARNER_ID, chapter=1)
    )
    assert not result.isError
    payload = result.structuredContent
    assert payload["chapter"] == 1
    assert payload["title"] == "Chapter 1: Variables and Data Types"
    assert payload["section"] is None
    assert "variable" in payload["content"].lower()


def test_get_chapter_content_section_via_http(server):
    asyncio.run(_call(server, tool="register_learner", name="Ada"))
    result = asyncio.run(
        _call(
            server,
            tool="get_chapter_content",
            learner_id=MOCK_LEARNER_ID,
            chapter=1,
            section="Code Examples",
        )
    )
    assert not result.isError
    payload = result.structuredContent
    assert payload["section"] == "Code Examples"
    assert "```python" in payload["content"]


def test_get_chapter_content_tier_gate_via_http(server):
    asyncio.run(_call(server, tool="register_learner", name="Ada"))
    result = asyncio.run(
        _call(server, tool="get_chapter_content", learner_id=MOCK_LEARNER_ID, chapter=6)
    )
    assert result.isError
    assert "paid plan" in result.content[0].text
    assert "tutorclaw.io/upgrade" in result.content[0].text


def test_get_exercises_all_via_http(server):
    asyncio.run(_call(server, tool="register_learner", name="Ada"))
    result = asyncio.run(
        _call(server, tool="get_exercises", learner_id=MOCK_LEARNER_ID, chapter=1)
    )
    assert not result.isError
    payload = result.structuredContent
    assert payload["chapter"] == 1
    assert payload["total"] == 3
    assert payload["filtered_by"] is None
    assert len(payload["exercises"]) == 3


def test_get_exercises_filtered_via_http(server):
    asyncio.run(_call(server, tool="register_learner", name="Ada"))
    result = asyncio.run(
        _call(
            server,
            tool="get_exercises",
            learner_id=MOCK_LEARNER_ID,
            chapter=2,
            weak_areas=["conditionals"],
        )
    )
    assert not result.isError
    payload = result.structuredContent
    assert payload["filtered_by"] == ["conditionals"]
    assert all(e["topic"] == "conditionals" for e in payload["exercises"])


def test_get_exercises_tier_gate_via_http(server):
    asyncio.run(_call(server, tool="register_learner", name="Ada"))
    result = asyncio.run(
        _call(server, tool="get_exercises", learner_id=MOCK_LEARNER_ID, chapter=6)
    )
    assert result.isError
    assert "paid plan" in result.content[0].text
    assert "tutorclaw.io/upgrade" in result.content[0].text


_SAMPLE_CHAPTER = """\
# Chapter 1: Variables

```python
name = "Alice"
print(name)
```

**Output:**
```
Alice
```
"""


def test_generate_guidance_predict_via_http(server):
    result = asyncio.run(
        _call(
            server,
            tool="generate_guidance",
            stage="predict",
            confidence=0.5,
            chapter_content=_SAMPLE_CHAPTER,
        )
    )
    assert not result.isError
    payload = result.structuredContent
    assert payload["stage"] == "predict"
    assert "```python" in payload["content"]
    assert "**Output:**" not in payload["content"]
    assert "PREDICT" in payload["system_prompt_addition"]


def test_generate_guidance_run_via_http(server):
    result = asyncio.run(
        _call(
            server,
            tool="generate_guidance",
            stage="run",
            confidence=0.8,
            chapter_content=_SAMPLE_CHAPTER,
        )
    )
    assert not result.isError
    payload = result.structuredContent
    assert payload["stage"] == "run"
    assert "**Output:**" in payload["content"]
    assert "challenge" in payload["system_prompt_addition"].lower()


def test_generate_guidance_invalid_stage_via_http(server):
    result = asyncio.run(
        _call(
            server,
            tool="generate_guidance",
            stage="modify",
            confidence=0.5,
            chapter_content=_SAMPLE_CHAPTER,
        )
    )
    assert result.isError
    assert "stage must be one of" in result.content[0].text


def test_assess_response_strong_via_http(server):
    result = asyncio.run(
        _call(
            server,
            tool="assess_response",
            answer_text="range generates a sequence used by the loop",
            primm_stage="predict",
            expected_concepts=["range", "sequence", "loop"],
        )
    )
    assert not result.isError
    payload = result.structuredContent
    assert payload["confidence_delta"] == pytest.approx(0.2)
    assert "Good answer" in payload["feedback"]
    assert payload["recommendation"] == "Advance to the run stage."


def test_assess_response_vague_via_http(server):
    result = asyncio.run(
        _call(
            server,
            tool="assess_response",
            answer_text="idk",
            primm_stage="run",
            expected_concepts=["range", "sequence"],
        )
    )
    assert not result.isError
    payload = result.structuredContent
    assert payload["confidence_delta"] == pytest.approx(-0.2)


def test_assess_response_invalid_stage_via_http(server):
    result = asyncio.run(
        _call(
            server,
            tool="assess_response",
            answer_text="some answer",
            primm_stage="modify",
            expected_concepts=["loop"],
        )
    )
    assert result.isError
    assert "stage must be one of" in result.content[0].text


def test_data_persisted_to_disk(server):
    """After HTTP calls, data file should exist on disk."""
    assert store.LEARNERS_FILE.exists()
    data = store._load()
    assert MOCK_LEARNER_ID in data


def test_get_upgrade_url_free_tier_via_http(server):
    asyncio.run(_call(server, tool="register_learner", name="Ada"))
    result = asyncio.run(
        _call(server, tool="get_upgrade_url", learner_id=MOCK_LEARNER_ID)
    )
    assert not result.isError
    payload = result.structuredContent
    assert payload["learner_id"] == MOCK_LEARNER_ID
    assert payload["tier"] == "free"
    assert payload["upgrade_url"].startswith("https://checkout.stripe.com/")


def test_get_upgrade_url_not_found_via_http(server):
    result = asyncio.run(
        _call(server, tool="get_upgrade_url", learner_id="nonexistent")
    )
    assert result.isError
    assert "learner not found" in result.content[0].text


def test_submit_code_success_via_http(server):
    result = asyncio.run(
        _call(server, tool="submit_code", code='print("hello from tutorclaw")')
    )
    assert not result.isError
    payload = result.structuredContent
    assert "hello from tutorclaw" in payload["stdout"]
    assert payload["timed_out"] is False
    assert payload["blocked_reason"] is None


def test_submit_code_blocked_import_via_http(server):
    result = asyncio.run(
        _call(server, tool="submit_code", code="import os\nprint(os.getcwd())")
    )
    assert not result.isError
    payload = result.structuredContent
    assert payload["blocked_reason"] is not None
    assert "os" in payload["blocked_reason"]
    assert payload["stdout"] == ""


def test_submit_code_runtime_error_via_http(server):
    result = asyncio.run(
        _call(server, tool="submit_code", code="print(1/0)")
    )
    assert not result.isError
    payload = result.structuredContent
    assert "ZeroDivisionError" in payload["stderr"]
    assert payload["blocked_reason"] is None
