# 014: Sidebar tree filter

## Контекст
User wants a quick filter in the object tree: typing `dic` should leave only tables/views/procedures with `dic` in the name.

## План изменений
1. [x] Add tests for sidebar filter input and searchable tree item attributes.
2. [x] Add tests for client-side filter JS hook.
3. [x] Add filter input to the dashboard sidebar.
4. [x] Add data attributes to sidebar sections/items.
5. [x] Implement client-side filtering and section count updates.
6. [x] Rebuild/restart Docker container.
7. [x] `just check` passes.

## Риски и открытые вопросы
- Filtering is client-side over already loaded object names. This is appropriate for current tree sizes and avoids extra routes.

## Верификация
- Targeted pytest for component/static asset regressions.
- `just check`.
- Docker rebuild and smoke check that updated JS is served.
