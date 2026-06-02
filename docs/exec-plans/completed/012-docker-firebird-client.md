# 012: Docker Firebird client runtime

## Контекст
Docker container starts successfully, but `/connect` fails with: `The location of Firebird Client Library could not be determined.`
Runtime image installs Python packages but not the native Firebird client library required by `firebird-driver`.

## План изменений
1. [x] Install `libfbclient2` in the Docker runtime stage.
2. [x] Copy `uv.lock` into the Docker runtime stage and install with `uv sync --frozen`.
3. [x] Pass `SESSION_SECRET_KEY` through docker compose for encrypted session cookies.
4. [x] Rebuild and restart Docker container.
5. [x] Verify app responds and container can discover `libfbclient`.

## Риски и открытые вопросы
- This fixes remote Firebird connectivity. Embedded local database support remains separate and documented in `docs/runtime/firebird-musl-bundle.md`.

## Верификация
- `docker compose up -d --build`
- `docker exec firebird-viewer ... libfbclient ...`
- `curl -I http://localhost:5001/`
