# 011: Hardening and doc sync

## Контекст
После первичного аудита найдены явные недоделки: session cookie подписан, но не зашифрован; `/ai/execute` выполняет любой SQL; CRUD не сверяет имена таблиц/колонок с metadata; DDL viewer показывает слишком упрощённый DDL; документация рассинхронизирована с текущим offline-assets/build flow.

## План изменений
1. [x] Добавить failing tests для encrypted session cookie.
2. [x] Добавить failing tests для `/ai/execute` validation.
3. [x] Добавить failing tests для CRUD identifier validation.
4. [x] Добавить failing tests для DDL defaults/computed columns.
5. [x] Реализовать минимальные изменения в interface/application/repository/domain.
6. [x] Обновить docs/CLAUDE/architecture под текущую реальность.
7. [x] `just check` проходит.

## Риски и открытые вопросы
- Полная генерация Firebird DDL включает constraints, indexes, triggers, domains и sequences. В этой задаче делаем ограниченный, проверяемый шаг: defaults/computed columns и явная пометка оставшихся ограничений.
- SQL editor намеренно остаётся arbitrary SQL execution surface.

## Верификация
- Targeted pytest для новых тестов.
- Полный `just check`.
