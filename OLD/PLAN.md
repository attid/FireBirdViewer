# Development Plan

## Roadmap

### Phase 1: MVP (Current Status)
- [x] Repository setup and Docker.
- [x] "Quick Connect" mode (Stateless).
- [x] View list of tables.
- [x] Execute arbitrary SQL (SELECT).
- [x] Display results in a table (Data Grid).
- [x] Fix UI/UX issues (Layout, Tailwind integration).
- [x] Rename project to "FireBirdViewer".

### Phase 2: v0.5 (Data Management & Polish)
- [x] VirtualScroller implementation for large tables.
- [x] Backend support for pagination (limit, offset, total count).
- [x] Update support using `RDB$DB_KEY`.
- [x] Edit records in Data Grid (UI implementation).
    - [x] Create Modal Dialog for editing.
    - [x] Identify types (Integer vs String vs BLOB).
    - [x] Create / Delete records.
- [ ] Support editing, uploading, and downloading BLOB data.
- [ ] **Firebird 4/5 Support:** Ensure SQL queries are compatible with modern Firebird versions (ODS 13+).
    - [ ] Detect Server/ODS Version on connect.
- [x] DDL Viewer (Show Create Table).
- [x] SQL Editor with syntax highlighting (Monaco/CodeMirror).

### Phase 3: v1.0 (Workspace & Security)
- [ ] **Authorization Mode (Stateful):**
    - [ ] Local SQLite database for settings.
    - [ ] Secure login (WebAuthn/Passkey preferred).
    - [ ] Saved connections list (Workspace).
    - [ ] Encrypted password storage (AES-GCM) using user keys.
- [ ] Editors for Procedures/Triggers.
- [ ] Dark/Light theme toggle (Polished).
- [ ] Localization (i18n) - Russian/English.

## Current Tasks (Immediate)
- [x] **Table View Enhancements:**
    - [x] Implement Tabs: Data, DDL, Query.
    - [x] Implement Insert/Delete functionality.
    - [x] Implement DDL generation.
