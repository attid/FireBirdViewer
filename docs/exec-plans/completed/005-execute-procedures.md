# 005: Execute stored procedures

## Context

User wants to run stored procedures with input parameters and see results.

## Plan

1. [x] Port: add `execute_procedure(proc_name, params) -> QueryResult` to `DatabasePort`
2. [x] Repository: implement `execute_procedure` in `FirebirdRepository`
   - SUSPEND detection for selectable vs executable mode
   - Ordered params by RDB$PARAMETER_NUMBER
   - Empty string -> NULL, datetime T fix
3. [x] Use-case: add `ExecuteProcedureUseCase`
4. [x] UI: Execute button + param form + results table in `procedure_view`
5. [x] Route: `POST /object/proc/{name}/execute`
6. [x] Tests: unit test for `ExecuteProcedureUseCase` (22 tests total)
7. [x] `just check` passes

## Verification

- Procedure with no params: click Execute -> results shown
- Procedure with input params: form appears, fill, submit -> results
- Error in procedure -> clean error message
- `just check` green (22 tests)
