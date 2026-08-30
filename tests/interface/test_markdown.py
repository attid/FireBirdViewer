"""Tests for safe AI assistant Markdown rendering."""

from src.domain.models import AiMessage
from src.interface.components.ai import ai_assistant_message
from src.interface.markdown import render_ai_markdown


def test_render_ai_markdown_formats_common_content():
    html = str(render_ai_markdown("**TASK** has *records*.\n\n- first\n- second\n\n`SELECT 1`"))

    assert "<strong>TASK</strong>" in html
    assert "<em>records</em>" in html
    assert "<ul" in html
    assert "<li>first</li>" in html
    assert "<code>SELECT 1</code>" in html


def test_render_ai_markdown_formats_tables_and_code_blocks():
    html = str(
        render_ai_markdown(
            "| ID | Name |\n| --- | --- |\n| 1 | Alice |\n\n```sql\nSELECT * FROM TASK;\n```"
        )
    )

    assert '<div class="overflow-x-auto' in html
    assert '<table class="table table-xs' in html
    assert "<th>ID</th>" in html
    assert "<td>Alice</td>" in html
    assert '<code class="language-sql">SELECT * FROM TASK;' in html


def test_render_ai_markdown_escapes_html_and_blocks_unsafe_links():
    html = str(
        render_ai_markdown(
            '<script>alert("xss")</script>\n\n[bad](javascript:alert(1))\n\n'
            "[good](https://example.com)"
        )
    )

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert 'href="javascript:' not in html
    assert 'href="https://example.com"' in html
    assert 'rel="noopener noreferrer"' in html


def test_render_ai_markdown_does_not_embed_images():
    html = str(render_ai_markdown("![tracking](https://example.com/tracking.png)"))

    assert "<img" not in html


def test_ai_assistant_message_renders_markdown_in_reply():
    html = str(ai_assistant_message(AiMessage(role="assistant", content="**1524** rows")))

    assert "<strong>1524</strong>" in html
    assert "**1524**" not in html
