from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from tutorclaw.tools.learners import get_learner_state, register_learner

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


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
