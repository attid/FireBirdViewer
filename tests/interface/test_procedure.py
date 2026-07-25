"""Tests for stored procedure components."""

from src.domain.models import ProcedureInfo, ProcedureParam
from src.interface.components.procedure import procedure_view


def test_procedure_form_renders_nullable_boolean_select():
    procedure = ProcedureInfo(
        name="SET_ALARM",
        params=[
            ProcedureParam(name="ENABLED", type_name="BOOLEAN", param_type=0),
        ],
    )

    html = str(procedure_view(procedure))

    assert '<select name="param_ENABLED"' in html
    assert '<option value="" selected>NULL</option>' in html
    assert '<option value="TRUE">TRUE</option>' in html
    assert '<option value="FALSE">FALSE</option>' in html
    assert 'placeholder="BOOLEAN"' not in html
