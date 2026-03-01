# 005: Execute stored procedures

## Context

User wants to run stored procedures with input parameters and see results.
Old Go project checked for SUSPEND keyword in source to determine if
procedure is selectable (returns rows via SELECT * FROM proc(...)) or
executable (EXECUTE PROCEDURE proc(...)). Both modes return a result set.

## Plan

1. [ ] Port: add `execute_procedure(proc_name, params: dict[str, str]) -> QueryResult` to `DatabasePort`
2. [ ] Repository: implement `execute_procedure` in `FirebirdRepository`
   - Check source for SUSPEND -> selectable vs executable
   - Build params in RDB$PARAMETER_NUMBER order
   - Selectable: `SELECT * FROM "PROC"(:p0, :p1)`
   - Executable: `EXECUTE PROCEDURE "PROC"(:p0, :p1)`
   - Return QueryResult with columns + rows
3. [ ] Use-case: add `ExecuteProcedureUseCase`
4. [ ] UI: add "Execute" button in `procedure_view`
   - If input params exist: show form with param fields
   - If no input params: execute immediately
   - Show results as a table below
5. [ ] Route: `POST /object/proc/{name}/execute` in `main.py`
   - Parse form params, call use-case
   - Return results component (table or error)
6. [ ] Tests: unit tests for `ExecuteProcedureUseCase`
7. [ ] `just check` passes

## Risks

- SUSPEND detection is heuristic (source may be obfuscated or empty)
- Procedures with BLOB params not supported in form
- Long-running procedures may time out

## Verification

- Procedure with no params: click Execute -> results shown
- Procedure with input params: form appears, fill, submit -> results
- Error in procedure -> clean error message
- `just check` green
