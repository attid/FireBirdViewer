# 017: Insert rows with generated fields

## Контекст

Insert-форма помечала каждую `NOT NULL` колонку HTML-атрибутом `required`.
Из-за этого браузер блокировал отправку формы, если generated primary key
оставался пустым. После снятия браузерной проверки repository всё равно
передавал пустое значение как явный `NULL`, не позволяя Firebird применить
default или `BEFORE INSERT` trigger.

Пользователь подтвердил этот план и точный список файлов сообщением `++`.

## План изменений

1. [x] Добавить regression-тест: insert-форма не блокирует пустые `NOT NULL`
   поля на стороне браузера.
2. [x] Добавить regression-тест: repository исключает пустые колонки из SQL.
3. [x] Убедиться, что новые тесты падают на старом поведении.
4. [x] Убрать HTML `required` из insert-формы.
5. [x] Исключать пустые значения из формируемого `INSERT`, сохраняя проверку
   неизвестных и computed-колонок.
6. [x] Повторить targeted-тесты и Playwright-проверку.
7. [x] Выполнить `just check`.
8. [x] Перенести план в `docs/exec-plans/completed/` до коммита.

## Согласованный список файлов

- Изменить `src/interface/components/crud.py`.
- Изменить `src/repository/firebird.py`.
- Изменить `tests/interface/test_paths.py`.
- Изменить `tests/repository/test_firebird.py`.
- Создать `docs/exec-plans/active/017-insert-generated-fields.md`.
- Перед коммитом перенести план в
  `docs/exec-plans/completed/017-insert-generated-fields.md`.

Другие файлы изменять запрещено без повторного подтверждения пользователя.

## Риски и открытые вопросы

- Пустое поле insert-формы означает «не включать колонку в SQL», чтобы
  Firebird применил default или trigger.
- Явный `NULL` через пустую строку insert-форма не задаёт.
- Если обязательная колонка не имеет default/trigger, Firebird вернёт
  validation error, который интерфейс покажет внутри формы.

## Верификация

- `uv run pytest
  tests/interface/test_paths.py::test_insert_form_does_not_block_blank_not_null_fields
  tests/repository/test_firebird.py::test_insert_row_omits_blank_columns_to_allow_defaults_and_triggers
  -q`
- Playwright: пустой `ALARM_ID`, заполненный `DESK_ID`, `form.checkValidity()`
  возвращает `true`.
- `just check`.
- `git diff --check`.
