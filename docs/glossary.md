# Glossary (Ubiquitous Language)

Domain terms used consistently across code, docs, and conversations.

| Term | Definition |
|------|-----------|
| **Connection** | A set of parameters (host, path, user, password) identifying a Firebird database |
| **DSN** | Data Source Name -- SQLAlchemy connection string built from connection params |
| **Object** | A database object: table, view, or stored procedure |
| **Table** | A Firebird user table (not system, not a view) |
| **View** | A Firebird user view (has RDB$VIEW_BLR) |
| **Procedure** | A Firebird stored procedure |
| **Column** | A field in a table or view, with type, nullability, and PK metadata |
| **DDL** | Data Definition Language -- the CREATE TABLE statement for a table |
| **PagedData** | A page of table rows with pagination metadata (page, page_size, total_count) |
| **Repository** | The infrastructure layer that executes SQL against Firebird |
| **Port** | An abstract interface in `application/` that repository implements |
| **Use-Case** | An application-layer function orchestrating a single user action |
| **Session** | Encrypted cookie containing connection params |
| **RDB$** | Prefix for Firebird system tables (metadata catalog) |
| **RDB$DB_KEY** | Firebird's internal row identifier (pseudo-column) |
| **FIRST N SKIP M** | Firebird's pagination syntax (equivalent to LIMIT/OFFSET) |
| **Selectable procedure** | A procedure containing SUSPEND, queried with SELECT |
| **Executable procedure** | A procedure without SUSPEND, called with EXECUTE PROCEDURE |
