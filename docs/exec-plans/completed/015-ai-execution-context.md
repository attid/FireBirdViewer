# 015: AI execution result context

## Контекст
AI DML execution results are rendered in chat, but not passed back into the next `/ai/ask`.
The user can see an error, while the agent cannot.

## План изменений
1. [x] Add tests that DML result rendering emits hidden AI context.
2. [x] Add tests that client JS sends `ai_context` with AI ask requests.
3. [x] Include `ai_context` in the next agent question.
4. [x] Rebuild/restart Docker container.
5. [x] `just check` passes.

## Риски и открытые вопросы
- This is a targeted context fix. A larger AG2 migration is intentionally out of scope.

## Верификация
- Targeted pytest.
- `just check`.
- Docker smoke check.
