# TutorClaw MCP

An MCP server built for **OpenClaw** that turns the learner's OpenClaw instance into a programming tutor. Learners progress through chapters using the **PRIMM-Lite** pedagogy — *Predict → Run → Investigate → Modify → Make* — while TutorClaw tracks state, serves content, gates tiers, and handles Stripe upgrades.

TutorClaw follows the **platform-inversion** model: OpenClaw provides the compute, messaging, and agent orchestration on the learner's side; TutorClaw provides only tools, content, and teaching logic — no database, no cloud, just JSON and markdown on disk.

---

## Features

- **9 MCP tools** covering learner state, content delivery, pedagogy, code execution, and billing
- **PRIMM-Lite methodology** — stage-appropriate prompts and assessment built into the tools
- **Local-first storage** — learners and progress in JSON, chapters in markdown, exercises in JSON
- **Tier gating** — free tier caps (chapters 1–5, 50 exchanges/day, 10 code submissions/day); paid tier unlimited
- **Stripe integration** — `get_upgrade_url` creates a checkout session; `/webhook` endpoint verifies `checkout.session.completed` and flips the learner to paid
- **Sandboxed code execution** — blocks `os`, `subprocess`, `shutil`, `open()`; 5-second timeout per submission
- **Streamable-HTTP transport** — stateless, FastMCP, port 8000

---

## The 9 Tools

| Tool | Purpose |
|------|---------|
| `register_learner` | Create a new learner and return their ID + API key |
| `get_learner_state` | Read chapter, stage, confidence, tier, exchanges remaining |
| `update_progress` | Advance chapter/stage and apply a confidence delta |
| `get_chapter_content` | Fetch chapter markdown, optionally narrowed to a section |
| `get_exercises` | Return practice problems, optionally filtered by weak areas |
| `generate_guidance` | Produce a stage-appropriate code excerpt and teaching system prompt |
| `assess_response` | Score a learner's answer against expected concepts |
| `submit_code` | Execute Python code in a sandbox with import and builtin restrictions |
| `get_upgrade_url` | Create a Stripe checkout session for a free-tier learner |

---

## Project Layout

```
tutorclaw-mcp/
├── src/tutorclaw/
│   ├── server.py          # FastMCP server, tool registration, /webhook route
│   ├── store.py           # JSON persistence, tier checks, quota tracking
│   ├── webhook.py         # Stripe checkout.session.completed handler
│   └── tools/
│       ├── learners.py    # register_learner, get_learner_state, update_progress
│       ├── content.py     # get_chapter_content, get_exercises
│       ├── guidance.py    # generate_guidance
│       ├── assessment.py  # assess_response
│       ├── execution.py   # submit_code (sandboxed)
│       └── billing.py     # get_upgrade_url
├── content/
│   ├── chapters/          # 01-variables.md … 05-files.md (free), 06+ (paid)
│   └── exercises/         # 01-exercises.json … 05-exercises.json
├── data/                  # Runtime state (gitignored): learners.json, learner_state.json
├── tests/                 # Per-tool unit tests + integration + payment-flow suites
├── AGENTS.md              # Agent instructions: session-start + tutoring flow
├── CLAUDE.md              # Build rules (uv, flat Annotated params, streamable-http)
└── pyproject.toml
```

---

## Requirements

- Python **3.14+**
- [uv](https://docs.astral.sh/uv/) for dependency management
- A Stripe account (test mode is fine) for the upgrade flow

---

## Setup

```bash
# Clone
git clone https://github.com/mohsinsheikhani/tutorclaw-mcp.git
cd tutorclaw-mcp

# Install dependencies
uv sync

# Configure Stripe (required only for get_upgrade_url and /webhook)
cp .env.example .env
# Edit .env and fill in:
#   STRIPE_SECRET_KEY=sk_test_...
#   STRIPE_PRICE_ID_PAID=price_...
#   STRIPE_WEBHOOK_SECRET=whsec_...
```

---

## Running the Server

```bash
uv run tutorclaw
```

The server starts on `http://0.0.0.0:8000` with streamable-HTTP stateless transport. The MCP endpoint is `/mcp` and the Stripe webhook is `/webhook`.

### Connect with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

Point it at `http://localhost:8000/mcp` and explore the 9 tools.

### Stripe webhook (local testing)

```bash
stripe listen --forward-to localhost:8000/webhook
# Copy the printed whsec_... into .env as STRIPE_WEBHOOK_SECRET
stripe trigger checkout.session.completed
```

---

## Tier Gating

| Limit | Free | Paid |
|-------|------|------|
| Chapters accessible | 1–5 | All |
| Exchanges per day | 50 | Unlimited |
| Code submissions per day | 10 | Unlimited |

Daily counters reset automatically at the first request after the reset date rolls over. Tools raise a `ValueError` with an upgrade hint when any gate trips.

---

## Storage Model

- **`data/learners.json`** — `{learner_id: {name, email, tier, api_key, created_at}}`
- **`data/learner_state.json`** — `{learner_id: {chapter, stage, confidence, exchanges_remaining, exchanges_reset_date, code_submissions_today, weak_areas}}`

Writes are atomic (temp-file + `os.replace`). Both files are gitignored.

---

## Testing

```bash
uv run pytest
```

The suite covers every tool with both unit and integration tests, plus a full payment-flow test (checkout session creation → webhook verification → tier upgrade). All tests use isolated `tmp_path` fixtures, so the production `data/` directory is never touched.

---

## Agent Usage

Drop `AGENTS.md` into the agent's context — it defines the session-start protocol, the tutoring flow, and the tool-selection rules:

1. On first message: `get_learner_state` → `register_learner` if missing.
2. For a lesson: `get_chapter_content` → `generate_guidance` → present → `assess_response` → `update_progress`.
3. For practice: `get_exercises`.
4. For code: `submit_code` (never `assess_response`).
5. On tier block: `get_upgrade_url`.

---

## License

MIT
