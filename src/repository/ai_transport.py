"""OpenAI-compatible server transport and response normalization."""

from typing import Any

import httpx
from pydantic import BaseModel, Field

from src.domain.models import (
    AiModelRequest,
    AiModelResponse,
    AiModelResponseMessage,
    AiToolCall,
)


class _ProviderFunction(BaseModel):
    name: str
    arguments: str = "{}"


class _ProviderToolCall(BaseModel):
    id: str
    function: _ProviderFunction


class _ProviderMessage(BaseModel):
    role: str = "assistant"
    content: str | None = ""
    tool_calls: list[_ProviderToolCall] = Field(default_factory=list)


class _ProviderChoice(BaseModel):
    message: _ProviderMessage


class _ProviderResponse(BaseModel):
    choices: list[_ProviderChoice]


def model_request_body(request: AiModelRequest) -> dict[str, Any]:
    """Convert a provider-neutral request into OpenAI Chat Completions JSON."""
    messages: list[dict[str, Any]] = []
    for message in request.messages:
        item: dict[str, Any] = {"role": message.role, "content": message.content}
        if message.tool_calls:
            item["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in message.tool_calls
            ]
        if message.tool_call_id:
            item["tool_call_id"] = message.tool_call_id
        messages.append(item)

    tools = [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in request.tools
    ]
    body: dict[str, Any] = {"model": request.model, "messages": messages}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    return body


def normalize_model_response(payload: object) -> AiModelResponse:
    """Validate and normalize an OpenAI-compatible response payload."""
    parsed = _ProviderResponse.model_validate(payload)
    if not parsed.choices:
        msg = "The AI provider returned no choices"
        raise ValueError(msg)
    message = parsed.choices[0].message
    return AiModelResponse(
        message=AiModelResponseMessage(
            content=message.content or "",
            tool_calls=[
                AiToolCall(
                    id=call.id,
                    name=call.function.name,
                    arguments=call.function.arguments,
                )
                for call in message.tool_calls
            ],
        )
    )


async def request_model(
    request: AiModelRequest,
    api_key: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> AiModelResponse:
    """Execute a model request with a server-managed API key."""
    url = f"{request.base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = model_request_body(request)
    if client is not None:
        response = await client.post(url, headers=headers, json=body)
    else:
        async with httpx.AsyncClient(timeout=60.0) as owned_client:
            response = await owned_client.post(url, headers=headers, json=body)
    response.raise_for_status()
    return normalize_model_response(response.json())
