"""AI Assistant components."""

import re
from re import Pattern

from fasthtml.common import *

from src.domain.models import AiMessage, QueryResult
from src.interface.paths import url_path


def ai_assistant() -> Div:
    """AI SQL Assistant page with chat area and settings."""
    return Div(
        Div(
            H3("AI SQL Assistant", cls="text-lg font-bold"),
            Div(
                Button(
                    "Clear",
                    cls="btn btn-ghost btn-sm",
                    onclick="window.__clearAiChat()",
                ),
                Button(
                    "Settings",
                    cls="btn btn-ghost btn-sm",
                    onclick="document.getElementById('ai-settings-modal').showModal()",
                ),
                cls="flex gap-1",
            ),
            cls="flex items-center justify-between mb-3",
        ),
        _ai_settings_modal(),
        Div(
            Div(
                P(
                    "Ask questions about your database in natural language. "
                    "I can query data, explain schemas, and suggest SQL.",
                    cls="text-base-content/60 text-sm text-center",
                ),
                cls="p-4",
            ),
            id="ai-chat-messages",
            cls="bg-base-200 rounded-box p-4 mb-3 overflow-y-auto",
            style="min-height: 300px; max-height: 60vh;",
        ),
        Form(
            Div(
                Input(
                    type="text",
                    name="question",
                    id="ai-question-input",
                    placeholder="Ask a question about your database...",
                    cls="input input-bordered flex-1",
                    autocomplete="off",
                ),
                Button(
                    "Ask",
                    type="submit",
                    cls="btn btn-primary",
                    id="ai-ask-btn",
                ),
                cls="flex gap-2",
            ),
            id="ai-ask-form",
            hx_post=url_path("/ai/ask"),
            hx_target="#ai-chat-messages",
            hx_swap="beforeend",
            hx_indicator="#ai-loading",
        ),
        Div(
            Span(cls="loading loading-dots loading-sm"),
            Span("Thinking...", cls="text-sm text-base-content/60 ml-2"),
            id="ai-loading",
            cls="htmx-indicator flex items-center gap-1 mt-2",
        ),
        Div(id="ai-history-data", cls="hidden"),
        cls="card bg-base-100 shadow p-4",
    )


def _ai_settings_modal() -> Dialog:
    """DaisyUI modal for AI settings (base_url, api_key, model)."""
    return Dialog(
        Div(
            Div(
                Div("AI", cls="badge badge-primary badge-sm text-primary-content"),
                H3("AI Settings", cls="font-bold text-2xl mt-2"),
                P(
                    "Configure your OpenAI-compatible API. Settings are stored in "
                    "your browser (localStorage) and sent with each request.",
                    cls="text-sm text-base-content/70 mt-2 leading-relaxed",
                ),
                cls="px-6 pt-6 pb-4 border-b border-base-300 bg-base-200",
            ),
            Div(
                Div(
                    Label(
                        Span("API Base URL", cls="label-text font-semibold text-sm"),
                        cls="label py-0 pb-2",
                    ),
                    Input(
                        type="text",
                        id="ai-base-url",
                        placeholder="https://api.openai.com/v1",
                        cls="input input-bordered w-full",
                    ),
                    P(
                        "Example: OpenAI, OpenRouter, local proxy",
                        cls="text-xs text-base-content/60 mt-2",
                    ),
                    cls="form-control rounded-box border border-base-300 bg-base-100 p-4",
                ),
                Div(
                    Label(
                        Span("API Key", cls="label-text font-semibold text-sm"),
                        cls="label py-0 pb-2",
                    ),
                    Input(
                        type="password",
                        id="ai-api-key",
                        placeholder="sk-...",
                        cls="input input-bordered w-full",
                        autocomplete="off",
                    ),
                    P("Stored only in your browser", cls="text-xs text-base-content/60 mt-2"),
                    cls="form-control rounded-box border border-base-300 bg-base-100 p-4",
                ),
                Div(
                    Label(
                        Span("Model", cls="label-text font-semibold text-sm"),
                        cls="label py-0 pb-2",
                    ),
                    Input(
                        type="text",
                        id="ai-model",
                        placeholder="gpt-4o-mini",
                        cls="input input-bordered w-full",
                    ),
                    P(
                        "Any model id supported by your provider",
                        cls="text-xs text-base-content/60 mt-2",
                    ),
                    cls="form-control rounded-box border border-base-300 bg-base-100 p-4",
                ),
                cls="px-6 py-5 space-y-4",
            ),
            Div(
                Div(
                    Button(
                        "Save",
                        cls="btn btn-primary btn-sm min-w-24",
                        onclick="window.__saveAiSettings(); "
                        "document.getElementById('ai-settings-modal').close()",
                    ),
                    Button(
                        "Cancel",
                        cls="btn btn-outline btn-sm min-w-24",
                        onclick="document.getElementById('ai-settings-modal').close()",
                    ),
                    cls="w-full flex items-center justify-end gap-2",
                ),
                cls="px-6 pb-6 pt-3 border-t border-base-300 bg-base-100",
            ),
            cls="modal-box w-11/12 max-w-xl p-0 shadow-2xl border border-base-300",
        ),
        Form(method="dialog", cls="modal-backdrop"),
        id="ai-settings-modal",
        cls="modal",
    )


def ai_user_message(question: str) -> Div:
    """Render a user message bubble in the chat."""
    return Div(
        Div(
            P(question),
            cls="chat-bubble chat-bubble-primary",
        ),
        cls="chat chat-end",
    )


_code_fence_pattern: Pattern[str] = re.compile(r"```\w*\s*\n(.*?)```", re.DOTALL)


def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences (```...```) from text for clean display."""
    return _code_fence_pattern.sub(r"\1", text).strip()


def ai_assistant_message(msg: AiMessage) -> Div:
    """Render an assistant message bubble with optional SQL and results."""
    parts = []

    display_text = _strip_code_fences(msg.content)
    parts.append(
        Div(
            display_text,
            cls="text-sm whitespace-pre-wrap break-words bg-base-200 p-3 rounded-box mb-2",
        )
    )

    if msg.sql and msg.is_dml:
        parts.append(
            Div(
                H4("Suggested SQL (requires confirmation):", cls="text-sm font-semibold mb-1"),
                Pre(
                    Code(msg.sql, cls="language-sql text-sm"),
                    cls="bg-base-300 p-2 rounded-box mb-2",
                ),
                Form(
                    Input(type="hidden", name="sql", value=msg.sql),
                    Button(
                        "Execute",
                        type="submit",
                        cls="btn btn-warning btn-sm",
                        hx_confirm="Execute this DML statement?",
                    ),
                    hx_post=url_path("/ai/execute"),
                    hx_target="#ai-chat-messages",
                    hx_swap="beforeend",
                ),
                cls="border border-warning/30 rounded-box p-3 mb-2",
            )
        )

    if msg.result and msg.result.columns:
        parts.append(_ai_results_table(msg.result))
    elif msg.result and msg.result.error:
        parts.append(
            Div(
                Span(f"Error: {msg.result.error}"),
                cls="alert alert-error text-sm mb-2",
            )
        )

    return Div(
        Div(
            *parts,
            cls="chat-bubble chat-bubble-accent max-w-full",
        ),
        cls="chat chat-start",
    )


def _ai_results_table(result: QueryResult) -> Div:
    """Render inline results table for AI chat."""
    header = Tr(*[Th(col, cls="text-xs") for col in result.columns])
    body_rows = []
    for row in result.rows[:100]:
        cells = []
        for val in row:
            display = str(val) if val is not None else "NULL"
            if len(display) > 100:
                display = display[:100] + "..."
            null_cls = "text-base-content/40 italic" if val is None else ""
            cells.append(Td(display, cls=f"text-xs {null_cls}"))
        body_rows.append(Tr(*cells, cls="hover"))

    extra = ""
    if len(result.rows) > 100:
        extra = P(
            f"Showing 100 of {len(result.rows)} rows",
            cls="text-xs text-base-content/50 mt-1",
        )

    return Div(
        Span(f"{result.row_count} rows", cls="badge badge-sm badge-ghost mb-1"),
        Div(
            Table(
                Thead(header),
                Tbody(*body_rows),
                cls="table table-xs table-pin-rows",
            ),
            cls="overflow-x-auto max-h-[40vh]",
        ),
        extra,
        cls="mb-2",
    )


def _ai_context_payload(result: QueryResult, sql: str) -> Div:
    """Hidden OOB context so the next AI turn can see execution results."""
    if result.error:
        text = f"Previous confirmed SQL failed.\nSQL:\n{sql}\nError:\n{result.error}"
    elif result.columns:
        text = f"Previous confirmed SQL returned {result.row_count} rows.\nSQL:\n{sql}"
    else:
        text = (
            "Previous confirmed SQL executed successfully. "
            f"Rows affected: {result.row_count}.\nSQL:\n{sql}"
        )

    return Div(text, id="ai-context-data", cls="hidden", hx_swap_oob="true")


def ai_dml_result(result: QueryResult, sql: str = "") -> Div:
    """Render the result of a user-confirmed DML execution."""
    if result.error:
        return Div(
            Div(
                Span(f"Error: {result.error}"),
                cls="chat-bubble chat-bubble-error",
            ),
            _ai_context_payload(result, sql),
            cls="chat chat-start",
        )

    if result.columns:
        return Div(
            Div(
                _ai_results_table(result),
                cls="chat-bubble chat-bubble-accent max-w-full",
            ),
            _ai_context_payload(result, sql),
            cls="chat chat-start",
        )

    return Div(
        Div(
            Span(f"Executed successfully. Rows affected: {result.row_count}"),
            cls="chat-bubble chat-bubble-success",
        ),
        _ai_context_payload(result, sql),
        cls="chat chat-start",
    )
