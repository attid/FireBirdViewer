"""Layout components: page wrapper, navbar, footer, connect form, dashboard."""

from fasthtml.common import *

from ._shared import _APP_VERSION, _GITHUB_URL, _read_version


def page_layout(*content, title: str = "FireBird Viewer"):
    """Wrap content in the base page layout with navbar."""
    return Div(
        _navbar(title),
        Div(*content, cls="container mx-auto max-w-7xl p-4"),
        Div(id="toast-container", cls="toast toast-end toast-top z-50"),
        _footer(),
        cls="min-h-screen bg-base-200",
    )


def _footer():
    """Page footer with GitHub link and version."""
    return Footer(
        Div(
            A(
                "GitHub",
                href=_GITHUB_URL,
                target="_blank",
                cls="link link-hover",
            ),
            Span(f" · v{_APP_VERSION}", cls="text-base-content/30"),
            cls="text-center text-sm text-base-content/50 py-4",
        ),
    )


def _navbar(title: str):
    """Top navigation bar."""
    return Div(
        Div(
            A(title, cls="text-xl font-bold", href="/"),
            cls="navbar bg-base-300 rounded-box mb-4 shadow",
        ),
        cls="container mx-auto max-w-7xl px-4 pt-4",
    )


def connect_form(database: str = "", user: str = ""):
    """Database connection form. Preserves values on error (except password)."""
    return Div(
        Div(
            H2("Connect to Firebird", cls="text-2xl font-bold mb-6 text-center"),
            Form(
                _form_field(
                    "Database",
                    "database",
                    "host:path or alias, e.g. localhost:employee",
                    value=database,
                ),
                _form_field("User", "user", "SYSDBA", value=user),
                Div(
                    Label("Password", cls="label"),
                    Input(
                        type="password",
                        name="password",
                        placeholder="password",
                        cls="input input-bordered w-full",
                        autocomplete="off",
                    ),
                    cls="form-control mb-4",
                ),
                Button("Connect", type="submit", cls="btn btn-primary w-full mt-2"),
                hx_post="/connect",
                hx_target="body",
                hx_swap="innerHTML",
            ),
            Div(id="connect-error", cls="mt-4"),
            Div(id="recent-connections", cls="mt-6"),
            cls="card bg-base-100 shadow-xl p-8 w-full max-w-md",
        ),
        cls="flex items-center justify-center min-h-[60vh]",
    )


def _form_field(label: str, name: str, placeholder: str, value: str = ""):
    """A labeled text input field."""
    return Div(
        Label(label, cls="label"),
        Input(
            type="text",
            name=name,
            placeholder=placeholder,
            value=value,
            cls="input input-bordered w-full",
        ),
        cls="form-control mb-4",
    )


def dashboard_layout(tables: list[str], views: list[str], procedures: list[str], db_name: str):
    """Main dashboard with sidebar tree + content area."""
    return Div(
        _navbar(f"FireBird Viewer - {db_name}"),
        Div(
            # Sidebar
            Div(
                Div(
                    A(
                        Span("SQL", cls="badge badge-sm badge-info mr-2"),
                        Span("SQL Editor"),
                        hx_get="/sql-editor",
                        hx_target="#content-area",
                        hx_swap="innerHTML",
                        cls="flex items-center p-2 rounded hover:bg-base-200"
                        " cursor-pointer text-sm font-semibold",
                    ),
                    cls="mb-2",
                ),
                Div(
                    A(
                        Span("AI", cls="badge badge-sm badge-warning mr-2"),
                        Span("AI Assistant"),
                        hx_get="/ai",
                        hx_target="#content-area",
                        hx_swap="innerHTML",
                        cls="flex items-center p-2 rounded hover:bg-base-200"
                        " cursor-pointer text-sm font-semibold",
                    ),
                    cls="mb-4",
                ),
                _sidebar_section("Tables", tables, "table", icon="T"),
                _sidebar_section("Views", views, "view", icon="V"),
                _sidebar_section("Procedures", procedures, "proc", icon="P"),
                Div(
                    A(
                        "Disconnect",
                        href="/disconnect",
                        cls="btn btn-outline btn-error btn-sm w-full mt-4",
                    ),
                ),
                cls="w-64 min-w-64 bg-base-100 rounded-box p-4 shadow overflow-y-auto max-h-[80vh]",
            ),
            # Content area
            Div(
                Div(
                    P(
                        "Select a table, view, or procedure from the sidebar.",
                        cls="text-base-content/60",
                    ),
                    cls="card bg-base-100 shadow p-8 text-center",
                ),
                id="content-area",
                cls="flex-1 min-w-0",
            ),
            cls="container mx-auto max-w-7xl px-4 flex gap-4",
        ),
        Div(id="toast-container", cls="toast toast-end toast-top z-50"),
        cls="min-h-screen bg-base-200",
    )


def _sidebar_section(title: str, items: list[str], item_type: str, icon: str = ""):
    """Collapsible sidebar section with list of items."""
    if not items:
        return Div(
            H3(f"{title} (0)", cls="font-semibold text-sm text-base-content/60 mb-1"),
            cls="mb-4",
        )

    item_links = []
    for item_name in items:
        badge_cls = {
            "table": "badge-primary",
            "view": "badge-secondary",
            "proc": "badge-accent",
        }.get(item_type, "badge-ghost")

        item_links.append(
            A(
                Span(icon, cls=f"badge badge-sm {badge_cls} mr-2"),
                Span(item_name, cls="truncate"),
                hx_get=f"/object/{item_type}/{item_name}",
                hx_target="#content-area",
                hx_swap="innerHTML",
                cls="flex items-center p-1.5 rounded hover:bg-base-200 cursor-pointer text-sm",
            )
        )

    return Div(
        Details(
            Summary(
                f"{title} ({len(items)})",
                cls="font-semibold text-sm cursor-pointer mb-1",
            ),
            Div(*item_links, cls="ml-2"),
            open=True,
        ),
        cls="mb-4",
    )
