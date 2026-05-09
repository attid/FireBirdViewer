"""Components package - re-exports all public functions for backward compatibility."""

from src.interface.components.ai import (
    ai_assistant,
    ai_assistant_message,
    ai_dml_result,
    ai_user_message,
)
from src.interface.components.crud import insert_form
from src.interface.components.data import (
    data_table,
    ddl_view,
)
from src.interface.components.layout import (
    connect_form,
    dashboard_layout,
    page_layout,
)
from src.interface.components.procedure import error_alert, procedure_result, procedure_view
from src.interface.components.sql import query_result, sql_editor, toast

__all__ = [
    "ai_assistant",
    "ai_assistant_message",
    "ai_dml_result",
    "ai_user_message",
    "connect_form",
    "dashboard_layout",
    "data_table",
    "ddl_view",
    "error_alert",
    "insert_form",
    "page_layout",
    "procedure_result",
    "procedure_view",
    "query_result",
    "sql_editor",
    "toast",
]
