# ADR-003: Browser-Relayed AI for Personal Credentials

## Status

Accepted

## Context

Organizations can configure one server-managed LLM credential for all users. Some
deployments prohibit outbound Internet access from the FireBirdViewer server, while an
individual user's browser can reach an external OpenAI-compatible provider with a
personal API key. Sending that key through FireBirdViewer would neither solve the
network restriction nor preserve browser-only credential ownership.

Maintaining separate agent implementations in Python and JavaScript would duplicate
prompts, tools, validation, conversation behavior, and security controls.

## Decision

Keep one provider-neutral agent loop on the backend and support two LLM transports:

- server-managed transport performs the provider request on the backend with runtime
  `AI_*` configuration;
- Browser BYOK returns the same request envelope to the browser, which adds its local
  API key and calls the provider directly.

The browser sends only the provider response back to FireBirdViewer. Backend-owned,
encrypted state carries the conversation between stateless request/response steps.
All database tools remain backend-executed and validated. Personal API keys are kept
in tab memory by default and are persisted only after explicit user opt-in.

The implementation uses the OpenAI Chat Completions message and function-tool format
as the compatibility contract. PydanticAI is removed because its model call is coupled
to its internal agent run. AG2 remains a future option for multi-agent workflows, but
its client-side tool abstraction does not directly provide browser-relayed LLM calls.

## Consequences

- Browser BYOK works when the server has no outbound Internet access.
- A personal API key is never sent to or logged by FireBirdViewer.
- Both credential modes share prompts, tool validation, SQL behavior, and history.
- Browser providers must allow CORS and must use HTTPS when FireBirdViewer uses HTTPS.
- Questions, schema details, and query results are disclosed to the provider selected
  by the user; the settings UI states this explicitly.
- OpenAI-compatible providers with incomplete function-tool support may fail with a
  clear provider or validation error.
