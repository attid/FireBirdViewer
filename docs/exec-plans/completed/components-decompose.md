# components-decompose: Split monolithic components.py (~1069 lines)

## Контекст
`src/interface/components.py` — 1069 строк, target: <300 строк/файл. Нарушает принцип локализации ответственности и conventions.md.

## План изменений

### Шаг 1: Создать `src/interface/components/` pkg
```
src/interface/components/
  __init__.py       -- re-export all public functions
  layout.py         -- page_layout, _navbar, _footer, connect_form, _form_field,
                       dashboard_layout, _sidebar_section
  data.py           -- data_table, _pagination_controls, _object_tabs, ddl_view
  procedure.py      -- procedure_view, _procedure_execute_form, procedure_result
  crud.py           -- insert_form
  sql.py            -- sql_editor, query_result, error_alert, toast
  ai.py             -- ai_assistant, _ai_settings_modal, ai_user_message,
                       _strip_code_fences, ai_assistant_message,
                       _ai_results_table, ai_dml_result
```

### Шаг 2: Общий код
`_read_version()`, `_APP_VERSION`, `_GITHUB_URL` — вынести в `src/interface/components/_shared.py` (импортируется из pkg).

### Шаг 3: Обновить main.py
Заменить `from src.interface.components import (..., ...)` на модульные импорты.

### Шаг 4: Удалить `src/interface/components.py`

### Шаг 5: `just check`

## Верификация
- `just check` (fmt + lint + arch-test + test) проходит
- Старт `just run` без ошибок импорта
- Все 15 публичных функций доступны
