package repository

import (
	"database/sql"
	"firebird-web-admin/internal/domain"
	"fmt"
	"log"
	"strings"

	_ "github.com/nakagami/firebirdsql"
)

type Repository interface {
	TestConnection(params domain.ConnectionParams) error
	ListTables(params domain.ConnectionParams) ([]domain.Table, error)
	GetData(params domain.ConnectionParams, tableName string, limit, offset int) ([]map[string]interface{}, []domain.Column, error)
	GetTotalCount(params domain.ConnectionParams, tableName string) (int, error)
	UpdateData(params domain.ConnectionParams, tableName string, dbKey string, data map[string]interface{}) error
	ListViews(params domain.ConnectionParams) ([]domain.Table, error)
	ListProcedures(params domain.ConnectionParams) ([]domain.Table, error)
	GetProcedureSource(params domain.ConnectionParams, procName string) (string, error)
}

type FirebirdRepository struct{}

func NewFirebirdRepository() *FirebirdRepository {
	return &FirebirdRepository{}
}

func (r *FirebirdRepository) getConnectionString(params domain.ConnectionParams) string {
	db := params.Database
	if colonIdx := strings.Index(db, ":"); colonIdx != -1 {
		if slashIdx := strings.LastIndex(db[:colonIdx], "/"); slashIdx != -1 {
			host := db[:slashIdx]
			port := db[slashIdx+1 : colonIdx]
			path := db[colonIdx+1:]
			db = fmt.Sprintf("%s:%s/%s", host, port, path)
		} else {
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
		log.Printf("Error opening connection: %v", err)
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

	query := `
		SELECT RDB$RELATION_NAME
		FROM RDB$RELATIONS
		WHERE RDB$VIEW_BLR IS NULL
		AND (RDB$SYSTEM_FLAG IS NULL OR RDB$SYSTEM_FLAG = 0)
		ORDER BY RDB$RELATION_NAME
	`
	rows, err := db.Query(query)
	if err != nil {
		log.Printf("ListTables error: %v", err)
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

func (r *FirebirdRepository) GetData(params domain.ConnectionParams, tableName string, limit, offset int) ([]map[string]interface{}, []domain.Column, error) {
	connStr := r.getConnectionString(params)
	db, err := sql.Open("firebirdsql", connStr)
	if err != nil {
		return nil, nil, err
	}
	defer db.Close()

	// Use FIRST/SKIP syntax for pagination
	// Fetching RDB$DB_KEY as hex string to identify rows for updates
	// Using table alias 't' to support "t.*" along with "t.RDB$DB_KEY" which is safer/required in some FB versions
	query := fmt.Sprintf("SELECT FIRST %d SKIP %d t.RDB$DB_KEY, t.* FROM \"%s\" t", limit, offset, tableName)
	log.Printf("GetData Query: %s", query)

	rows, err := db.Query(query)
	if err != nil {
		log.Printf("GetData DB Error: %v", err)
		return nil, nil, err
	}
	defer rows.Close()

	colNames, err := rows.Columns()
	if err != nil {
		log.Printf("GetData Columns Error: %v", err)
		return nil, nil, err
	}

	colTypes, err := rows.ColumnTypes()
	if err != nil {
		log.Printf("GetData ColumnTypes Error: %v", err)
		return nil, nil, err
	}

	var cols []domain.Column
	for i, ct := range colTypes {
		cols = append(cols, domain.Column{
			Name: colNames[i],
			Type: ct.DatabaseTypeName(),
		})
	}

	var result []map[string]interface{}

	for rows.Next() {
		values := make([]interface{}, len(colNames))
		valuePtrs := make([]interface{}, len(colNames))
		for i := range values {
			valuePtrs[i] = &values[i]
		}

		if err := rows.Scan(valuePtrs...); err != nil {
			log.Printf("GetData Scan Error: %v", err)
			return nil, nil, err
		}

		entry := make(map[string]interface{})
		for i, col := range colNames {
			var v interface{}
			val := values[i]
			b, ok := val.([]byte)
			if ok {
				// Special handling for RDB$DB_KEY: encode as Hex for frontend
				if col == "DB_KEY" || col == "RDB$DB_KEY" {
					v = fmt.Sprintf("%x", b)
				} else {
					v = string(b)
				}
			} else {
				v = val
			}
			entry[col] = v
		}
		result = append(result, entry)
	}
	return result, cols, nil
}

func (r *FirebirdRepository) GetTotalCount(params domain.ConnectionParams, tableName string) (int, error) {
	connStr := r.getConnectionString(params)
	db, err := sql.Open("firebirdsql", connStr)
	if err != nil {
		return 0, err
	}
	defer db.Close()

	query := fmt.Sprintf("SELECT COUNT(*) FROM \"%s\"", tableName)
	log.Printf("GetTotalCount Query: %s", query)
	var count int
	if err := db.QueryRow(query).Scan(&count); err != nil {
		log.Printf("GetTotalCount Error: %v", err)
		return 0, err
	}
	return count, nil
}

func (r *FirebirdRepository) UpdateData(params domain.ConnectionParams, tableName string, dbKey string, data map[string]interface{}) error {
	connStr := r.getConnectionString(params)
	db, err := sql.Open("firebirdsql", connStr)
	if err != nil {
		return err
	}
	defer db.Close()

	setClauses := []string{}
	args := []interface{}{}

	for col, val := range data {
		// Skip DB_KEY in update
		if col == "RDB$DB_KEY" || col == "DB_KEY" {
			continue
		}
		setClauses = append(setClauses, fmt.Sprintf("\"%s\" = ?", col))
		args = append(args, val)
	}

	if len(setClauses) == 0 {
		return nil
	}

	// Convert hex string dbKey back to bytes
	var keyBytes []byte
	_, err = fmt.Sscanf(dbKey, "%x", &keyBytes)
	if err != nil {
		return fmt.Errorf("invalid db_key format")
	}
	args = append(args, keyBytes)

	query := fmt.Sprintf("UPDATE \"%s\" SET %s WHERE RDB$DB_KEY = ?", tableName, strings.Join(setClauses, ", "))
	log.Printf("UpdateData Query: %s, Args: %v", query, args)

	_, err = db.Exec(query, args...)
	if err != nil {
		log.Printf("UpdateData Error: %v", err)
	}
	return err
}

func (r *FirebirdRepository) ListViews(params domain.ConnectionParams) ([]domain.Table, error) {
	connStr := r.getConnectionString(params)
	db, err := sql.Open("firebirdsql", connStr)
	if err != nil {
		return nil, err
	}
	defer db.Close()

	query := `
		SELECT RDB$RELATION_NAME
		FROM RDB$RELATIONS
		WHERE RDB$VIEW_BLR IS NOT NULL
		AND (RDB$SYSTEM_FLAG IS NULL OR RDB$SYSTEM_FLAG = 0)
		ORDER BY RDB$RELATION_NAME
	`
	rows, err := db.Query(query)
	if err != nil {
		log.Printf("ListViews error: %v", err)
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

func (r *FirebirdRepository) ListProcedures(params domain.ConnectionParams) ([]domain.Table, error) {
	connStr := r.getConnectionString(params)
	db, err := sql.Open("firebirdsql", connStr)
	if err != nil {
		return nil, err
	}
	defer db.Close()

	query := `
		SELECT RDB$PROCEDURE_NAME
		FROM RDB$PROCEDURES
		WHERE (RDB$SYSTEM_FLAG IS NULL OR RDB$SYSTEM_FLAG = 0)
		ORDER BY RDB$PROCEDURE_NAME
	`
	rows, err := db.Query(query)
	if err != nil {
		log.Printf("ListProcedures error: %v", err)
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

func (r *FirebirdRepository) GetProcedureSource(params domain.ConnectionParams, procName string) (string, error) {
	connStr := r.getConnectionString(params)
	db, err := sql.Open("firebirdsql", connStr)
	if err != nil {
		return "", err
	}
	defer db.Close()

	query := `
		SELECT RDB$PROCEDURE_SOURCE
		FROM RDB$PROCEDURES
		WHERE RDB$PROCEDURE_NAME = ?
	`
	var source sql.NullString
	// Firebird usually stores names in uppercase, but let's try exact match first or handle case sensitivity.
	// Usually system tables store uppercase. The user provided input might be whatever.
	// For now, let's assume exact match.
	if err := db.QueryRow(query, strings.ToUpper(procName)).Scan(&source); err != nil {
		log.Printf("GetProcedureSource error: %v", err)
		return "", err
	}

	if source.Valid {
		return source.String, nil
	}
	return "", nil
}
