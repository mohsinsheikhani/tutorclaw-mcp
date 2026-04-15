from __future__ import annotations

import asyncio
import subprocess
import sys
import time

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "http://127.0.0.1:8000/mcp"


@pytest.fixture(scope="module")
def server():
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


async def _call(url: str, **kwargs):
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert any(t.name == "register_learner" for t in tools.tools)
            return await session.call_tool("register_learner", kwargs)


def test_register_via_http(server):
    result = asyncio.run(_call(server, name="Ada"))
    assert not result.isError
    payload = result.structuredContent
    assert payload["name"] == "Ada"
    assert payload["learner_id"].startswith("lrn_")
    assert payload["email"] is None
    assert "Ada" in payload["welcome_message"]


def test_register_with_email_via_http(server):
    result = asyncio.run(_call(server, name="Grace", email="grace@example.com"))
    assert not result.isError
    assert result.structuredContent["email"] == "grace@example.com"


def test_invalid_email_via_http(server):
    result = asyncio.run(_call(server, name="Bad", email="not-an-email"))
    assert result.isError
    assert "valid address" in result.content[0].text
