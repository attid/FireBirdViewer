# Product roadmap

This roadmap records product directions rather than commitments or release
deadlines. Implement each item only after its behavior, security boundaries,
and verification plan are approved.

## Data management

- Upload, download, and edit BLOB values.
- Export query and table results as CSV and JSON.
- Add richer per-column filtering where Firebird types support it.
- Evaluate virtual scrolling for result sets where pagination is not the best
  interaction model.

## Database objects

- Browse triggers and generators/sequences.
- Edit procedure and trigger source with an explicit execution confirmation.
- Expand generated DDL to cover more Firebird metadata.
- Detect Firebird server and ODS versions when compatibility decisions require
  them.

## Workspace

- Save named connections without exposing credentials to the browser.
- Add an authenticated workspace mode with encrypted credential storage.
- Keep the current stateless quick-connect mode available.

## Editor and interface

- Store optional SQL query history locally in the browser.
- Add light and dark theme controls.
- Add Russian and English localization.
- Improve progress feedback for long-running database operations.

