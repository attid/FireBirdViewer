# Exec-Plan 007: Offline Vendor Assets + Docker

## Goal
All JS/CSS dependencies served locally from `static/vendor/` so the app
runs fully offline inside a Docker container (no internet required at runtime).

## Tasks

- [x] Install npm devDependencies: tailwindcss, daisyui, esbuild, codemirror, lang-sql, htmx.org
- [x] Create `tailwind.config.js` scanning `src/`, `main.py` for class names
- [x] Create `static/src/input.css` with Tailwind directives + DaisyUI plugin
- [x] Create `static/src/codemirror-entry.js` for esbuild bundling
- [x] Build Tailwind+DaisyUI CSS -> `static/vendor/styles.css` (53KB)
- [x] Bundle CodeMirror 6 + lang-sql via esbuild -> `static/vendor/codemirror.bundle.js` (430KB)
- [x] Copy HTMX from node_modules -> `static/vendor/htmx.min.js` (50KB)
- [x] Update `codemirror-init.js` to use `window.__CM` from local bundle
- [x] Update `main.py` hdrs: removed all CDN refs, use `/static/vendor/` paths
- [x] Add `just build-vendor` + `npm run build` to justfile/package.json
- [x] Create multi-stage `Dockerfile` (node:20-slim -> python:3.13-slim)
- [x] Create `.dockerignore`
- [x] Run `just check` green (32 tests)

## Design Notes

- Tailwind CLI runs at Docker build time (stage 1), not runtime
- esbuild bundles CodeMirror into single IIFE file, exports via `window.__CM`
- `static/vendor/` contains generated artifacts (~533KB total)
- DaisyUI is a Tailwind plugin, included via `tailwind.config.js`
- HTMX installed as npm devDependency, copied from node_modules
- No internet required at container runtime
