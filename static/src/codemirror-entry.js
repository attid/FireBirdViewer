/**
 * CodeMirror 6 entry point for esbuild bundling.
 *
 * Exports EditorView, basicSetup, sql, and EditorState
 * as globals on window.__CM so codemirror-init.js can use them.
 */
import { EditorView, basicSetup } from "codemirror";
import { sql } from "@codemirror/lang-sql";
import { EditorState } from "@codemirror/state";

window.__CM = { EditorView, basicSetup, sql, EditorState };
