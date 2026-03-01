# Exec-Plan 008: AI SQL Assistant

## Goal
Add an AI-powered SQL assistant that accepts natural language queries,
generates SQL using the database schema as context, executes SELECT automatically,
and requires explicit user confirmation for any DML (INSERT/UPDATE/DELETE).

## Tasks

- [ ] Add `pydantic-ai[openai]` to pyproject.toml
- [ ] Add `AiSettings` model to `src/domain/models.py`
- [ ] Create `src/repository/ai_agent.py` — PydanticAI agent with tools
- [ ] Add `AskAiUseCase` to `src/application/use_cases.py`
- [ ] Add `ai_assistant()`, `ai_message()`, `ai_settings_form()` components
- [ ] Add routes: `GET /ai`, `POST /ai/ask`, `POST /ai/execute`, `POST /ai/settings`
- [ ] Add "AI Assistant" link in sidebar
- [ ] Add chat UI logic in `static/app.js`
- [ ] Add tests for use case and agent
- [ ] `just check` green

## Design

### LLM Config
- OpenAI-compatible API (works with OpenAI, Ollama, vLLM, etc.)
- Settings: base_url, api_key, model — from UI (localStorage) or env fallback
- Client sends settings in POST body; server does NOT persist secrets

### Agent Tools (PydanticAI)
- `get_schema()` — returns {table: [columns]} for all tables/views
- `execute_select(sql)` — runs read-only SELECT, returns results
- NO tool for DML — agent can only suggest DML SQL text

### Safety
- SELECT → auto-execute, show results inline
- DML → show SQL + "Execute" button, user must confirm
- Agent system prompt explicitly forbids direct DML execution

### UI
- Separate page (like SQL Editor) accessible from sidebar
- Chat-style: user messages + assistant responses
- Settings icon → modal/form for base_url, api_key, model
- Results tables rendered inline in chat
