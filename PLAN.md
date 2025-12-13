# Development Plan

## Roadmap

### Phase 1: MVP (Current Status)
- [x] Repository setup and Docker.
- [x] "Quick Connect" mode (Stateless).
- [x] View list of tables.
- [x] Execute arbitrary SQL (SELECT) - *Partially implemented via Grid? Need to verify SQL Editor presence.* (Note: SQL Editor not yet seen in code, focusing on Grid view first).
- [x] Display results in a table (Data Grid).
- [x] Fix UI/UX issues (Layout, Tailwind integration).
- [x] Rename project to "FireBirdViewer".

### Phase 2: v0.5 (Data Management & Polish)
- [x] VirtualScroller implementation for large tables.
- [x] Backend support for pagination (limit, offset, total count).
- [x] Update support using `RDB$DB_KEY`.
- [ ] Edit/Delete records in Data Grid (UI implementation pending).
- [ ] **Firebird 4/5 Support:** Ensure SQL queries are compatible with modern Firebird versions (ODS 13+).
    - [ ] Detect Server/ODS Version on connect.
- [ ] DDL Viewer (Show Create Table).
- [ ] SQL Editor with syntax highlighting (Monaco/CodeMirror).

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
- [x] **Fix Frontend Stack:** Install and configure Tailwind CSS.
- [x] **Login Page:**
    - [x] Implement Tabs: "Quick Connect" vs "Authorization".
    - [x] Fix form alignment.
- [x] **Dashboard:**
    - [x] Fix Sidebar/Content layout.
    - [x] Rename all titles to "FireBirdViewer".
    - [x] Implement VirtualScroller.
- [x] **Backend:**
    - [x] Fix pagination APIs.
    - [x] Fix SQL compatibility for Firebird 4/5 (Alias usage).
- [x] **Documentation:** Update README.
