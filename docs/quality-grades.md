# Quality Grades

Assessment of each layer/domain. Scale: A (excellent) to D (needs major work).

Updated: 2026-05-09 (main.py refactored to use use-cases)

| Layer / Module | Grade | Notes |
|---------------|-------|-------|
| `src/domain/models.py` | B | Clean Pydantic models. Missing: domain exceptions, value object validation |
| `src/application/` | D | Layer exists but is a thin passthrough. Needs real use-cases with business logic |
| `src/repository/firebird.py` | B | All SQL isolated, proper quoting. Missing: error wrapping, connection pooling tuning |
| `src/interface/components.py` | C | Functional but monolithic (370+ lines). Needs splitting by concern |
| `src/interface/session.py` | A- | Clean encrypted-cookie session with a persistent generated key and optional explicit override |
| `main.py` | B | Routes properly delegate to use-cases. Missing: input validation, authz checks |
| `tests/` | D | Minimal. Need unit tests for domain, integration tests for repository |
| `docs/` | B | All required docs created. Need to verify they stay in sync with code |
| `.linters/` | C | Import boundary check exists. Could add more structural tests |

## Tracked Debt

1. `main.py` refactored to delegate to use-cases instead of calling repo directly ✅
2. `components.py` exceeds 300-line target
3. Persist the generated session-key state directory across container replacement
4. No integration tests with actual Firebird
5. No structured logging (JSON format)
