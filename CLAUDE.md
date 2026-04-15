# TutorClaw MCP Server

## Rules

- Use the mcp-builder skill for all MCP work
- Use uv for Python projects
- Follow spec-first development: discuss requirements, output spec, then build
- Use flat Annotated parameters on tools, not Pydantic BaseModel wrappers
- Use streamable-http stateless transport on port 8000

## After every build

1. Write and run tests. Fix any failures before continuing.
2. Start the server and confirm it boots without errors.
3. Make real HTTP tool calls against the running server to verify end-to-end. And write integration tests
4. Kill the server process.
5. Report results, and ask: if user wants to start the server connect with MCP Inspector"
