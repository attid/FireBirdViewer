"""Firebird database repository using SQLAlchemy async.

All Firebird-specific SQL queries live here. The rest of the application
interacts with Firebird only through this module.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.application.ports import DatabasePort
from src.domain.models import (
    Column,
    ConnectionParams,
    PagedData,
    ProcedureInfo,
    ProcedureParam,
    QueryResult,
)

# Firebird internal type code -> human-readable name
_FB_TYPE_MAP: dict[int, str] = {
    7: "SMALLINT",
    8: "INTEGER",
    10: "FLOAT",
    12: "DATE",
    13: "TIME",
    14: "CHAR",
    16: "BIGINT",
    27: "DOUBLE PRECISION",
    35: "TIMESTAMP",
    37: "VARCHAR",
    261: "BLOB",
}


def _map_fb_type(
    type_code: int, sub_type: int | None, length: int | None, scale: int | None
) -> str:
    """Map Firebird internal type code to a human-readable SQL type name."""
    if type_code == 16 and sub_type and sub_type > 0:
        precision = length or 18
        s = abs(scale) if scale else 0
        return f"DECIMAL({precision},{s})"
    if type_code == 7 and sub_type and sub_type > 0:
        precision = length or 4
        s = abs(scale) if scale else 0
        return f"DECIMAL({precision},{s})"
    base = _FB_TYPE_MAP.get(type_code, f"UNKNOWN({type_code})")
    if type_code in (14, 37) and length:
        return f"{base}({length})"
    return base


def _quote(identifier: str) -> str:
    """Quote a Firebird identifier to prevent SQL injection."""
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


class FirebirdRepository(DatabasePort):
    """Async repository for Firebird database operations."""

    def __init__(self, params: ConnectionParams) -> None:
        self._params = params
        self._engine: AsyncEngine | None = None

    async def _get_engine(self) -> AsyncEngine:
        if self._engine is None:
            dsn = self._params.to_dsn()
            self._engine = create_async_engine(dsn, echo=False)
        return self._engine

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None

    async def test_connection(self) -> bool:
        """Test that the connection works."""
        engine = await self._get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1 FROM RDB$DATABASE"))
            row = result.fetchone()
            return row is not None

    async def list_tables(self) -> list[str]:
        """List all user tables (not views, not system)."""
        engine = await self._get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT TRIM(RDB$RELATION_NAME) FROM RDB$RELATIONS "
                    "WHERE RDB$VIEW_BLR IS NULL AND RDB$SYSTEM_FLAG = 0 "
                    "ORDER BY RDB$RELATION_NAME"
                )
            )
            return [row[0] for row in result.fetchall()]

    async def list_views(self) -> list[str]:
        """List all user views."""
        engine = await self._get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT TRIM(RDB$RELATION_NAME) FROM RDB$RELATIONS "
                    "WHERE RDB$VIEW_BLR IS NOT NULL AND RDB$SYSTEM_FLAG = 0 "
                    "ORDER BY RDB$RELATION_NAME"
                )
            )
            return [row[0] for row in result.fetchall()]

    async def list_procedures(self) -> list[str]:
        """List all stored procedures."""
        engine = await self._get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT TRIM(RDB$PROCEDURE_NAME) FROM RDB$PROCEDURES "
                    "WHERE RDB$SYSTEM_FLAG = 0 "
                    "ORDER BY RDB$PROCEDURE_NAME"
                )
            )
            return [row[0] for row in result.fetchall()]

    async def get_columns(self, table_name: str) -> list[Column]:
        """Get column metadata for a table or view."""
        engine = await self._get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT "
                    "  TRIM(rf.RDB$FIELD_NAME), "
                    "  f.RDB$FIELD_TYPE, "
                    "  f.RDB$FIELD_SUB_TYPE, "
                    "  f.RDB$FIELD_LENGTH, "
                    "  f.RDB$FIELD_SCALE, "
                    "  rf.RDB$NULL_FLAG, "
                    "  f.RDB$NULL_FLAG, "
                    "  rf.RDB$UPDATE_FLAG, "
                    "  COALESCE(rc.PK_FLAG, 0) "
                    "FROM RDB$RELATION_FIELDS rf "
                    "JOIN RDB$FIELDS f ON rf.RDB$FIELD_SOURCE = f.RDB$FIELD_NAME "
                    "LEFT JOIN ("
                    "  SELECT seg.RDB$FIELD_NAME, 1 AS PK_FLAG "
                    "  FROM RDB$RELATION_CONSTRAINTS rc "
                    "  JOIN RDB$INDEX_SEGMENTS seg ON rc.RDB$INDEX_NAME = seg.RDB$INDEX_NAME "
                    "  WHERE rc.RDB$CONSTRAINT_TYPE = 'PRIMARY KEY' "
                    "    AND TRIM(rc.RDB$RELATION_NAME) = :table_name"
                    ") rc ON TRIM(rc.RDB$FIELD_NAME) = TRIM(rf.RDB$FIELD_NAME) "
                    "WHERE TRIM(rf.RDB$RELATION_NAME) = :table_name "
                    "ORDER BY rf.RDB$FIELD_POSITION"
                ),
                {"table_name": table_name},
            )

            columns = []
            for row in result.fetchall():
                (
                    name,
                    type_code,
                    sub_type,
                    length,
                    scale,
                    rel_null_flag,
                    field_null_flag,
                    update_flag,
                    pk_flag,
                ) = row
                # NOT NULL can be set at relation level (rf) or domain level (f)
                is_not_null = (rel_null_flag is not None and rel_null_flag == 1) or (
                    field_null_flag is not None and field_null_flag == 1
                )
                columns.append(
                    Column(
                        name=name.strip() if name else name,
                        type_name=_map_fb_type(type_code, sub_type, length, scale),
                        nullable=not is_not_null,
                        is_primary_key=bool(pk_flag),
                        is_computed=update_flag is not None and update_flag == 0,
                    )
                )
            return columns

    async def get_table_data(
        self,
        table_name: str,
        page: int = 0,
        page_size: int = 50,
        sort_column: str | None = None,
        sort_dir: str = "ASC",
    ) -> PagedData:
        """Get paginated data from a table or view."""
        engine = await self._get_engine()
        columns = await self.get_columns(table_name)
        col_names = [c.name for c in columns]

        # Validate sort column
        if sort_column and sort_column not in col_names:
            sort_column = None
        if sort_dir.upper() not in ("ASC", "DESC"):
            sort_dir = "ASC"

        quoted_table = _quote(table_name)
        order_clause = ""
        if sort_column:
            order_clause = f" ORDER BY {_quote(sort_column)} {sort_dir.upper()}"

        offset = page * page_size
        # Include RDB$DB_KEY as first column for row identification (used by delete/update)
        query = (
            f"SELECT FIRST {page_size} SKIP {offset} "
            f"t.RDB$DB_KEY, t.* FROM {quoted_table} t{order_clause}"
        )
        count_query = f"SELECT COUNT(*) FROM {quoted_table}"

        async with engine.connect() as conn:
            result = await conn.execute(text(query))
            rows_raw = result.fetchall()

            count_result = await conn.execute(text(count_query))
            total = count_result.scalar() or 0

        rows = []
        for row in rows_raw:
            row_dict: dict = {}
            # First column is RDB$DB_KEY (bytes), encode as hex for transport
            db_key_raw = row[0]
            row_dict["_db_key"] = (
                db_key_raw.hex() if isinstance(db_key_raw, bytes) else str(db_key_raw)
            )
            # Remaining columns map to metadata columns
            for i, col in enumerate(columns):
                val = row[i + 1] if (i + 1) < len(row) else None
                if isinstance(val, bytes):
                    try:
                        val = val.decode("utf-8")
                    except UnicodeDecodeError:
                        val = val.hex()
                row_dict[col.name] = val
            rows.append(row_dict)

        return PagedData(
            columns=columns,
            rows=rows,
            total_count=total,
            page=page,
            page_size=page_size,
        )

    async def delete_row(self, table_name: str, db_key_hex: str) -> int:
        """Delete a row identified by RDB$DB_KEY (hex-encoded).

        Returns number of rows deleted (0 or 1).
        """
        engine = await self._get_engine()
        db_key_bytes = bytes.fromhex(db_key_hex)
        quoted_table = _quote(table_name)
        query = f"DELETE FROM {quoted_table} WHERE RDB$DB_KEY = :db_key"

        async with engine.connect() as conn:
            result = await conn.execute(text(query), {"db_key": db_key_bytes})
            await conn.commit()
            return result.rowcount or 0

    async def insert_row(self, table_name: str, data: dict[str, object]) -> None:
        """Insert a new row into a table.

        ``data`` maps column names to values. Empty strings are converted
        to ``None`` so that Firebird treats them as NULLs (avoids type
        coercion errors on numeric/date columns).
        """
        if not data:
            msg = "No data to insert"
            raise ValueError(msg)

        engine = await self._get_engine()
        quoted_table = _quote(table_name)

        col_clauses = []
        param_names = []
        param_values: dict[str, object] = {}
        for idx, (col_name, val) in enumerate(data.items()):
            col_clauses.append(_quote(col_name))
            param_key = f"p{idx}"
            param_names.append(f":{param_key}")
            # Treat empty strings as NULL (user left field blank)
            if val == "":
                param_values[param_key] = None
            else:
                # HTML datetime-local gives "2025-01-15T06:15" but Firebird
                # expects "2025-01-15 06:15" (T is parsed as timezone region)
                str_val = str(val)
                if "T" in str_val and len(str_val) >= 16 and str_val[10:11] == "T":
                    str_val = str_val.replace("T", " ", 1)
                param_values[param_key] = str_val

        cols_sql = ", ".join(col_clauses)
        vals_sql = ", ".join(param_names)
        query = f"INSERT INTO {quoted_table} ({cols_sql}) VALUES ({vals_sql})"

        async with engine.connect() as conn:
            await conn.execute(text(query), param_values)
            await conn.commit()

    async def get_ddl(self, table_name: str) -> str:
        """Generate a CREATE TABLE statement for the given table."""
        columns = await self.get_columns(table_name)
        pk_cols = [c.name for c in columns if c.is_primary_key]

        lines = []
        for col in columns:
            parts = [f"    {_quote(col.name)} {col.type_name}"]
            if not col.nullable:
                parts.append("NOT NULL")
            lines.append(" ".join(parts))

        if pk_cols:
            pk_list = ", ".join(_quote(c) for c in pk_cols)
            lines.append(f"    PRIMARY KEY ({pk_list})")

        body = ",\n".join(lines)
        return f"CREATE TABLE {_quote(table_name)} (\n{body}\n);"

    async def get_procedure_source(self, proc_name: str) -> ProcedureInfo:
        """Get stored procedure source code and parameters."""
        engine = await self._get_engine()
        async with engine.connect() as conn:
            # Source
            result = await conn.execute(
                text(
                    "SELECT RDB$PROCEDURE_SOURCE FROM RDB$PROCEDURES "
                    "WHERE TRIM(RDB$PROCEDURE_NAME) = :name"
                ),
                {"name": proc_name},
            )
            row = result.fetchone()
            source = ""
            if row and row[0]:
                source = (
                    row[0] if isinstance(row[0], str) else row[0].decode("utf-8", errors="replace")
                )

            # Parameters (input only for now)
            result = await conn.execute(
                text(
                    "SELECT "
                    "  TRIM(pp.RDB$PARAMETER_NAME), "
                    "  f.RDB$FIELD_TYPE, "
                    "  f.RDB$FIELD_SUB_TYPE, "
                    "  f.RDB$FIELD_LENGTH, "
                    "  f.RDB$FIELD_SCALE, "
                    "  pp.RDB$PARAMETER_TYPE "
                    "FROM RDB$PROCEDURE_PARAMETERS pp "
                    "JOIN RDB$FIELDS f ON pp.RDB$FIELD_SOURCE = f.RDB$FIELD_NAME "
                    "WHERE TRIM(pp.RDB$PROCEDURE_NAME) = :name "
                    "ORDER BY pp.RDB$PARAMETER_TYPE, pp.RDB$PARAMETER_NUMBER"
                ),
                {"name": proc_name},
            )

            params = []
            for row in result.fetchall():
                name, type_code, sub_type, length, scale, param_type = row
                params.append(
                    ProcedureParam(
                        name=name.strip() if name else name,
                        type_name=_map_fb_type(type_code, sub_type, length, scale),
                        param_type=param_type or 0,
                    )
                )

        return ProcedureInfo(name=proc_name, source=source, params=params)

    async def execute_query(self, sql: str) -> QueryResult:
        """Execute an arbitrary SQL query and return results."""
        engine = await self._get_engine()
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text(sql))
                if result.returns_rows:
                    cols = list(result.keys())
                    raw_rows = result.fetchall()
                    rows = []
                    for row in raw_rows:
                        processed = []
                        for val in row:
                            if isinstance(val, bytes):
                                processed.append(val.hex())
                            else:
                                processed.append(val)
                        rows.append(processed)
                    return QueryResult(
                        columns=cols,
                        rows=rows,
                        row_count=len(rows),
                    )
                else:
                    await conn.commit()
                    return QueryResult(row_count=result.rowcount or 0)
        except Exception as exc:
            return QueryResult(error=str(exc))
