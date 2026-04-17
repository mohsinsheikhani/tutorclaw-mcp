from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from tutorclaw.tools.assessment import assess_response
from tutorclaw.tools.billing import get_upgrade_url
from tutorclaw.tools.content import get_chapter_content, get_exercises
from tutorclaw.tools.execution import submit_code
from tutorclaw.tools.guidance import generate_guidance
from tutorclaw.tools.learners import get_learner_state, register_learner, update_progress
from tutorclaw.webhook import stripe_webhook

mcp = FastMCP(
    "tutorclaw",
    stateless_http=True,
    host="0.0.0.0",
    port=8000,
)

mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)(register_learner)

mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)(get_learner_state)

mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)(update_progress)


mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)(get_chapter_content)


mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)(get_exercises)


mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)(generate_guidance)


mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)(assess_response)


mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)(submit_code)


mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)(get_upgrade_url)


mcp.custom_route("/webhook", methods=["POST"])(stripe_webhook)


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
