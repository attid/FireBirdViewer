# 027: Browser-relayed AI transport

## Context

FireBirdViewer currently performs every LLM request on the backend through
PydanticAI. That prevents user-supplied API keys from working in installations
where the application server has no outbound Internet access. The approved
design keeps one backend-owned agent loop while allowing the browser to relay
LLM requests when the user supplies their own key.

The user approved this plan with `++` on 2026-08-30.

## Approved files

Create:

- `src/repository/ai_transport.py`
- `tests/repository/test_ai_transport.py`
- `tests/interface/test_ai_relay.py`
- `adr/003-browser-relayed-ai.md`
- `docs/exec-plans/active/027-browser-relayed-ai.md`

Modify:

- `src/domain/models.py`
- `src/application/use_cases.py`
- `src/repository/ai_agent.py`
- `src/interface/components/ai.py`
- `main.py`
- `static/app.js`
- `tests/repository/test_ai_agent.py`
- `tests/application/test_use_cases.py`
- `README.md`
- `docs/architecture.md`
- `pyproject.toml`
- `uv.lock`

Move on completion:

- `docs/exec-plans/active/027-browser-relayed-ai.md`
- to `docs/exec-plans/completed/027-browser-relayed-ai.md`

## Plan

- [x] Add typed model-request, model-response, and relay-state contracts.
- [x] Add failing tests for the provider-neutral agent loop and transports.
- [x] Implement one backend-owned OpenAI-compatible tool loop.
- [x] Implement server-managed and browser-relayed transports.
- [x] Keep BYOK credentials out of requests to FireBirdViewer.
- [x] Add browser mode selection, memory-only keys by default, and clear diagnostics.
- [x] Preserve SQL confirmation and execution context behavior.
- [x] Remove PydanticAI and update the dependency lock.
- [x] Record the architectural decision and update user documentation.
- [x] Verify both modes in the browser.
- [x] Rebuild the belief map without deleting generated map files.
- [x] Run `just check`.

## Risks and open questions

- Browser mode requires the chosen provider to allow CORS and HTTPS when the
  application itself is served over HTTPS.
- OpenAI-compatible providers vary in their support for tool calls.
- Browser networking policy must allow user-selected public endpoints without
  weakening unrelated application boundaries.
- The maximum number of agent steps is a resource-safety boundary, not a
  product limit.

## Verification

```text
uv run pytest tests/repository/test_ai_agent.py \
  tests/repository/test_ai_transport.py \
  tests/interface/test_ai_relay.py \
  tests/application/test_use_cases.py
just check
```

Browser verification through Orca:

1. Server-managed provider completes a schema/query tool cycle.
2. Browser BYOK completes the same cycle without sending the key to the app.
3. DDL/DML remains a suggestion requiring explicit confirmation.
4. CORS and mixed-content failures produce actionable UI errors.

## Result

- Browser BYOK completed a two-request model cycle with a backend `get_schema`
  tool call in Orca's embedded browser.
- Server-managed mode completed the same tool cycle through the backend.
- FireBirdViewer received only relay state and provider responses in BYOK mode;
  the test API key was sent directly to the provider.
- `just check` passed with 173 tests.
