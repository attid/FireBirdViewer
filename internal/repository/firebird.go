package repository

import (
	"database/sql"
	"firebird-web-admin/internal/domain"
	"fmt"
	"strings"

	_ "github.com/nakagami/firebirdsql"
)

type Repository interface {
	TestConnection(params domain.ConnectionParams) error
	ListTables(params domain.ConnectionParams) ([]domain.Table, error)
	GetData(params domain.ConnectionParams, tableName string) ([]map[string]interface{}, error)
}

type FirebirdRepository struct{}

func NewFirebirdRepository() *FirebirdRepository {
	return &FirebirdRepository{}
}

func (r *FirebirdRepository) getConnectionString(params domain.ConnectionParams) string {
	// Format: user:password@database_string
	// The firebirdsql driver uses net/url.Parse, which expects "user:password@host:port/path".
	// Firebird users often provide "host:path" or "host/port:path".
	// We need to normalize this to a URL-compatible format.

	db := params.Database

	// Check if the input is in "host/port:path" format (e.g., 127.0.0.1/3050:C:/db.fdb)
	if colonIdx := strings.Index(db, ":"); colonIdx != -1 {
		// Check for slash before colon (indicates port separator in Firebird syntax)
		if slashIdx := strings.LastIndex(db[:colonIdx], "/"); slashIdx != -1 {
			// Convert "host/port:path" -> "host:port/path"
			host := db[:slashIdx]
			port := db[slashIdx+1 : colonIdx]
			path := db[colonIdx+1:]
			db = fmt.Sprintf("%s:%s/%s", host, port, path)
		} else {
			// Convert "host:path" -> "host/path"
			// This handles "100.77.235.41:ac" -> "100.77.235.41/ac"
			host := db[:colonIdx]
			path := db[colonIdx+1:]
			db = fmt.Sprintf("%s/%s", host, path)
		}
	}

	return fmt.Sprintf("%s:%s@%s", params.User, params.Password, db)
}

func (r *FirebirdRepository) TestConnection(params domain.ConnectionParams) error {
	connStr := r.getConnectionString(params)
	db, err := sql.Open("firebirdsql", connStr)
	if err != nil {
		return err
	}
	defer db.Close()

	return db.Ping()
}

func (r *FirebirdRepository) ListTables(params domain.ConnectionParams) ([]domain.Table, error) {
	connStr := r.getConnectionString(params)
	db, err := sql.Open("firebirdsql", connStr)
	if err != nil {
		return nil, err
	}
	defer db.Close()

	// Query to list tables in Firebird
	// RDB$RELATIONS where RDB$VIEW_BLR is null (tables) and RDB$SYSTEM_FLAG is 0 (user tables)
	query := `
		SELECT RDB$RELATION_NAME
		FROM RDB$RELATIONS
		WHERE RDB$VIEW_BLR IS NULL
		AND (RDB$SYSTEM_FLAG IS NULL OR RDB$SYSTEM_FLAG = 0)
		ORDER BY RDB$RELATION_NAME
	`
	rows, err := db.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var tables []domain.Table
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			return nil, err
		}
		tables = append(tables, domain.Table{Name: strings.TrimSpace(name)})
	}
	return tables, nil
}

func (r *FirebirdRepository) GetData(params domain.ConnectionParams, tableName string) ([]map[string]interface{}, error) {
	connStr := r.getConnectionString(params)
	db, err := sql.Open("firebirdsql", connStr)
	if err != nil {
		return nil, err
	}
	defer db.Close()

	// WARNING: Basic implementation, vulnerable to SQL injection if tableName is not validated.
	// For MVP foundation, we assume tableName comes from our own ListTables list, but should be careful.
	// Firebird doesn't support parameterized table names.
	// Ideally we should quote the identifier.
	query := fmt.Sprintf("SELECT FIRST 100 * FROM \"%s\"", tableName)

	rows, err := db.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		return nil, err
	}

	var result []map[string]interface{}

	for rows.Next() {
		// Create a slice of interface{} to hold values
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range values {
			valuePtrs[i] = &values[i]
		}

		if err := rows.Scan(valuePtrs...); err != nil {
			return nil, err
		}

		entry := make(map[string]interface{})
		for i, col := range columns {
			var v interface{}
			val := values[i]
			b, ok := val.([]byte)
			if ok {
				v = string(b)
			} else {
				v = val
			}
			entry[col] = v
		}
		result = append(result, entry)
	}

	return result, nil
}
