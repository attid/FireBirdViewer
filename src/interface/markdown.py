"""Safe server-side Markdown rendering for AI assistant replies."""

from collections.abc import Sequence

from fasthtml.common import NotStr
from markdown_it import MarkdownIt
from markdown_it.token import Token


def _table_open(
    tokens: Sequence[Token],
    idx: int,
    options: dict,
    env: dict,
) -> str:
    """Wrap Markdown tables so wide results scroll inside the chat bubble."""
    return '<div class="overflow-x-auto max-w-full mb-2"><table class="table table-xs">'


def _table_close(
    tokens: Sequence[Token],
    idx: int,
    options: dict,
    env: dict,
) -> str:
    return "</table></div>"


def _configure_renderer() -> MarkdownIt:
    renderer = MarkdownIt(
        "commonmark",
        {
            "html": False,
            "linkify": False,
            "typographer": False,
        },
    )
    renderer.enable("table")
    renderer.disable("image")
    renderer.renderer.rules["table_open"] = _table_open
    renderer.renderer.rules["table_close"] = _table_close
    return renderer


_MARKDOWN = _configure_renderer()


def _style_tokens(tokens: Sequence[Token]) -> None:
    for token in tokens:
        if token.type == "paragraph_open":
            token.attrSet("class", "mb-2")
        elif token.type == "bullet_list_open":
            token.attrSet("style", "list-style: disc; margin: 0 0 0.5rem 1.25rem")
        elif token.type == "ordered_list_open":
            token.attrSet("style", "list-style: decimal; margin: 0 0 0.5rem 1.25rem")
        elif token.type == "blockquote_open":
            token.attrSet("class", "border-l-4 border-base-300 pl-4 mb-2")
        elif token.type == "link_open":
            token.attrSet("rel", "noopener noreferrer")
            token.attrSet("class", "link hover:underline")

        if token.children:
            _style_tokens(token.children)


def render_ai_markdown(text: str) -> NotStr:
    """Render untrusted model Markdown with raw HTML and images disabled."""
    tokens = _MARKDOWN.parse(text)
    _style_tokens(tokens)
    rendered = _MARKDOWN.renderer.render(tokens, _MARKDOWN.options, {})
    return NotStr(rendered)
