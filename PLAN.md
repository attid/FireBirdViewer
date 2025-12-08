# Development Plan

## Roadmap

### Phase 1: MVP (Current Status)
- [x] Repository setup and Docker.
- [x] "Quick Connect" mode (Stateless).
- [x] View list of tables.
- [x] Execute arbitrary SQL (SELECT) - *Partially implemented via Grid? Need to verify SQL Editor presence.* (Note: SQL Editor not yet seen in code, focusing on Grid view first).
- [x] Display results in a table (Data Grid).
- [ ] Fix UI/UX issues (Layout, Tailwind integration).
- [ ] Rename project to "FireBirdViewer".

### Phase 2: v0.5 (Data Management & Polish)
- [ ] VirtualScroller implementation for large tables.
- [ ] Edit/Delete records in Data Grid.
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
- [ ] **Fix Frontend Stack:** Install and configure Tailwind CSS to fix broken layouts.
- [ ] **Login Page:**
    - [ ] Implement Tabs: "Quick Connect" vs "Authorization".
    - [ ] "Authorization" tab as a visual placeholder ("Coming Soon").
    - [ ] Fix form alignment.
- [ ] **Dashboard:**
    - [ ] Fix Sidebar/Content layout.
    - [ ] Rename all titles to "FireBirdViewer".
- [ ] **Documentation:** Update README.
