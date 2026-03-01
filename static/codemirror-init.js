/* CodeMirror 6 initialization for SQL Editor.
 *
 * Depends on codemirror.bundle.js (loaded before this script) which
 * exposes window.__CM = { EditorView, basicSetup, sql, EditorState }.
 * Ctrl+Enter handled via DOM keydown listener.
 * Initialises editor when #cm-editor appears (after HTMX swap).
 */

var editorView = null;

function initEditor() {
    var CM = window.__CM;
    if (!CM) return;

    var container = document.getElementById("cm-editor");
    if (!container || container.dataset.cmInit) return;

    // Mark as initialized so we don't double-init
    container.dataset.cmInit = "1";

    // Read schema from data attribute for autocomplete
    var sqlConfig = {};
    var schemaData = container.dataset.schema;
    if (schemaData) {
        try {
            sqlConfig.schema = JSON.parse(schemaData);
        } catch (e) {
            // ignore parse errors
        }
    }
    sqlConfig.upperCaseKeywords = true;

    editorView = new CM.EditorView({
        state: CM.EditorState.create({
            doc: "",
            extensions: [CM.basicSetup, CM.sql(sqlConfig)],
        }),
        parent: container,
    });

    // Set reasonable height
    container.style.minHeight = "200px";

    // Ctrl+Enter / Cmd+Enter to execute
    container.addEventListener("keydown", function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            e.preventDefault();
            syncAndSubmit();
        }
    });
}

function syncAndSubmit() {
    if (!editorView) return;
    var textarea = document.getElementById("sql-textarea");
    if (textarea) {
        textarea.value = editorView.state.doc.toString();
    }
    // Trigger HTMX submit on the form
    var form = document.getElementById("sql-editor-form");
    if (form) {
        htmx.trigger(form, "submit");
    }
}

// Sync editor content to hidden textarea before any HTMX submit
document.addEventListener("htmx:configRequest", function (e) {
    var elt = e.detail.elt;
    if (!elt || !editorView) return;
    // Check if the triggering element is the form itself or inside it
    var form = elt.id === "sql-editor-form" ? elt : elt.closest("#sql-editor-form");
    if (form) {
        var textarea = document.getElementById("sql-textarea");
        if (textarea) {
            textarea.value = editorView.state.doc.toString();
        }
    }
});

// Initialize editor when content area is swapped (HTMX)
document.addEventListener("htmx:afterSwap", function () {
    // Small delay to ensure DOM is ready
    setTimeout(initEditor, 50);
});

// Also try on page load
document.addEventListener("DOMContentLoaded", function () {
    setTimeout(initEditor, 100);
});
