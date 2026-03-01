"""Ports (abstract interfaces) for infrastructure adapters.

Application layer defines WHAT operations are needed.
Infrastructure layer (repository/) defines HOW they are performed.
"""

from abc import ABC, abstractmethod

from src.domain.models import Column, PagedData, ProcedureInfo, QueryResult


class DatabasePort(ABC):
    """Abstract interface for database operations.

    Repository implementations must satisfy this contract.
    Application layer depends only on this abstraction, never on concrete repos.
    """

    @abstractmethod
    async def test_connection(self) -> bool: ...

    @abstractmethod
    async def list_tables(self) -> list[str]: ...

    @abstractmethod
    async def list_views(self) -> list[str]: ...

    @abstractmethod
    async def list_procedures(self) -> list[str]: ...

    @abstractmethod
    async def get_columns(self, table_name: str) -> list[Column]: ...

    @abstractmethod
    async def get_table_data(
        self,
        table_name: str,
        page: int = 0,
        page_size: int = 50,
        sort_column: str | None = None,
        sort_dir: str = "ASC",
    ) -> PagedData: ...

    @abstractmethod
    async def delete_row(self, table_name: str, db_key_hex: str) -> int: ...

    @abstractmethod
    async def insert_row(self, table_name: str, data: dict[str, object]) -> None: ...

    @abstractmethod
    async def update_cell(
        self, table_name: str, db_key_hex: str, column_name: str, value: object
    ) -> None: ...

    @abstractmethod
    async def get_ddl(self, table_name: str) -> str: ...

    @abstractmethod
    async def get_procedure_source(self, proc_name: str) -> ProcedureInfo: ...

    @abstractmethod
    async def execute_query(self, sql: str) -> QueryResult: ...

    @abstractmethod
    async def close(self) -> None: ...
