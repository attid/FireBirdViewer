# 018: Firebird scalar type coverage

## Контекст

Firebird metadata type code `23` отображается как `UNKNOWN(23)`, поэтому
BOOLEAN-поле получает обычный текстовый input. Существующая константа
`ALL_FILTER_COLUMN_TYPES` создаёт ложное впечатление полного покрытия, хотя
проверяет только безопасность фильтра для вручную выбранного подмножества
типов.

Официальный список `RDB$FIELD_TYPE` также включает современные типы Firebird:
`DECFLOAT(16)`, `DECFLOAT(34)`, `INT128`, `TIME WITH TIME ZONE` и
`TIMESTAMP WITH TIME ZONE`.

Пользователь подтвердил этот план и точный список файлов сообщением `++`.

## План изменений

1. [x] Добавить failing-тесты всех официальных scalar metadata type codes.
2. [x] Добавить failing-тесты `NUMERIC/DECIMAL` precision metadata.
3. [x] Добавить failing-тест BOOLEAN-фильтра по `true`/`false`.
4. [x] Добавить failing-тесты BOOLEAN-контролов insert/edit/procedure.
5. [x] Реализовать полный scalar type mapping и чтение precision metadata.
6. [x] Реализовать безопасный BOOLEAN-фильтр.
7. [x] Добавить общий BOOLEAN select для форм.
8. [x] Проверить UI через Playwright.
9. [x] Выполнить `just check`.
10. [x] Перенести план в `docs/exec-plans/completed/` до коммита.

## Согласованный список файлов

- Изменить `src/repository/firebird.py`.
- Создать `src/interface/components/form_fields.py`.
- Изменить `src/interface/components/crud.py`.
- Изменить `src/interface/components/procedure.py`.
- Изменить `tests/repository/test_firebird.py`.
- Изменить `tests/interface/test_paths.py`.
- Создать `tests/interface/test_procedure.py`.
- Создать `docs/exec-plans/active/018-firebird-scalar-types.md`.
- Перед коммитом перенести план в
  `docs/exec-plans/completed/018-firebird-scalar-types.md`.

Другие файлы изменять запрещено без повторного подтверждения пользователя.

## Риски и открытые вопросы

- Scope покрывает scalar-типы Firebird; массивы не входят в задачу.
- BOOLEAN insert использует три состояния: default, true и false.
- BOOLEAN edit использует true/false вместе с существующим NULL-контролом.
- Time-zone значения остаются текстовыми полями, чтобы браузерный
  `datetime-local` не удалял часовой пояс.

## Верификация

- Параметризованные unit-тесты всех scalar metadata codes.
- Unit-тесты SQL-предикатов BOOLEAN-фильтра.
- Component-тесты insert/edit/procedure BOOLEAN controls.
- Playwright-проверка выбора FALSE и сериализации form data.
- `just check`.
