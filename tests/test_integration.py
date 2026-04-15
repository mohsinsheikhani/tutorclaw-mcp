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


def test_data_persisted_to_disk(server):
    """After HTTP calls, data file should exist on disk."""
    assert store.LEARNERS_FILE.exists()
    data = store._load()
    assert MOCK_LEARNER_ID in data
