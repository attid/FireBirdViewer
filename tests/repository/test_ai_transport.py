"""Tests for the server-side OpenAI-compatible HTTP transport."""

import pytest

from src.domain.models import AiChatMessage, AiModelRequest
from src.repository.ai_transport import request_model


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"role": "assistant", "content": "Hello"}}]}


class FakeClient:
    def __init__(self):
        self.calls = []

    async def post(self, url, *, headers, json):
        self.calls.append((url, headers, json))
        return FakeResponse()


@pytest.mark.asyncio
async def test_request_model_adds_server_key_only_to_provider_request():
    client = FakeClient()
    request = AiModelRequest(
        base_url="https://llm.example/v1/",
        model="model-a",
        messages=[AiChatMessage(role="user", content="Hello")],
    )

    response = await request_model(request, "server-secret", client=client)

    assert response.message.content == "Hello"
    assert client.calls[0][0] == "https://llm.example/v1/chat/completions"
    assert client.calls[0][1]["Authorization"] == "Bearer server-secret"
    assert "server-secret" not in str(client.calls[0][2])
