"""Regression tests for dashboard sidebar filtering assets."""

from pathlib import Path

from src.interface.components.layout import dashboard_layout


def test_dashboard_sidebar_has_filter_input_and_searchable_items():
    html = str(dashboard_layout(["DIC_CITY", "CARDS"], [], ["GET_DIC"], "db"))

    assert 'id="sidebar-filter"' in html
    assert 'data-sidebar-item="true"' in html
    assert 'data-filter-name="dic_city"' in html
    assert 'data-filter-name="get_dic"' in html
    assert 'data-sidebar-section="true"' in html
    assert 'data-section-title="Tables"' in html


def test_app_js_contains_sidebar_filter_hook():
    js = Path("static/app.js").read_text(encoding="utf-8")

    assert "sidebar-filter" in js
    assert "data-filter-name" in js
    assert "data-section-visible-count" in js
