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
	GetData(params domain.ConnectionParams, tableName string, limit, offset int, sortField string, sortOrder string) ([]map[string]interface{}, []domain.Column, error)
	GetTotalCount(params domain.ConnectionParams, tableName string) (int, error)
	UpdateData(params domain.ConnectionParams, tableName string, dbKey string, data map[string]interface{}) error
	ListViews(params domain.ConnectionParams) ([]domain.Table, error)
	ListProcedures(params domain.ConnectionParams) ([]domain.Table, error)
	GetProcedureSource(params domain.ConnectionParams, procName string) (string, error)
	GetProcedureParameters(params domain.ConnectionParams, procName string) ([]domain.ProcedureParameter, error)
	ExecuteProcedure(params domain.ConnectionParams, procName string, inputParams map[string]interface{}) ([]map[string]interface{}, []domain.Column, error)
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

func (r *FirebirdRepository) GetData(params domain.ConnectionParams, tableName string, limit, offset int, sortField string, sortOrder string) ([]map[string]interface{}, []domain.Column, error) {
	connStr := r.getConnectionString(params)
	db, err := sql.Open("firebirdsql", connStr)
	if err != nil {
		return nil, nil, err
	}
	defer db.Close()

	// Use FIRST/SKIP syntax for pagination
	// Fetching RDB$DB_KEY as hex string to identify rows for updates
	// Using table alias 't' to support "t.*" along with "t.RDB$DB_KEY" which is safer/required in some FB versions

	// Sorting
	orderByClause := ""
	if sortField != "" {
		// Sanitize/Quote sortField. Firebird identifiers in double quotes are case sensitive and allow spaces.
		// We trust the input to be a valid column name or minimal sanity check.
		// Simple anti-SQL injection: ensure it doesn't contain quotes or semicolons, or just quote it.
		// Quoting is safest for valid identifiers.
		// NOTE: sortField should be sanitized more rigorously in a real app or checked against columns.
		// For now we assume typical column names.
		safeField := strings.ReplaceAll(sortField, "\"", "") // remove quotes if any
		safeField = "\"" + safeField + "\""

		order := "ASC"
		if strings.ToUpper(sortOrder) == "DESC" || sortOrder == "-1" {
			order = "DESC"
		}

		orderByClause = fmt.Sprintf("ORDER BY %s %s", safeField, order)
	}

	// For Firebird: SELECT FIRST N SKIP M ... ORDER BY ...
	query := fmt.Sprintf("SELECT FIRST %d SKIP %d t.RDB$DB_KEY, t.* FROM \"%s\" t %s", limit, offset, tableName, orderByClause)
	log.Printf("GetData Query: %s", query)

	rows, err := db.Query(query)
	if err != nil {
		log.Printf("GetData DB Error: %v", err)
		return nil, nil, err
	}
	defer rows.Close()

	return r.scanRows(rows, tableName, db)
}

// scanRows is a helper to process result rows and metadata
func (r *FirebirdRepository) scanRows(rows *sql.Rows, relationName string, db *sql.DB) ([]map[string]interface{}, []domain.Column, error) {
	colNames, err := rows.Columns()
	if err != nil {
		log.Printf("scanRows Columns Error: %v", err)
		return nil, nil, err
	}

	colTypes, err := rows.ColumnTypes()
	if err != nil {
		log.Printf("scanRows ColumnTypes Error: %v", err)
		return nil, nil, err
	}

	// Fetch metadata to identify ReadOnly columns (computed)
	// RDB$UPDATE_FLAG: 1 = regular, 0 = computed (read-only)
	// We only do this if relationName is provided (it might be empty for procedure results)
	readOnlyMap := make(map[string]bool)
	if relationName != "" {
		metaQuery := `
			SELECT RDB$FIELD_NAME, RDB$UPDATE_FLAG
			FROM RDB$RELATION_FIELDS
			WHERE RDB$RELATION_NAME = ?
		`
		metaRows, err := db.Query(metaQuery, relationName)
		if err == nil {
			defer metaRows.Close()
			for metaRows.Next() {
				var fName string
				var uFlag sql.NullInt64
				if err := metaRows.Scan(&fName, &uFlag); err == nil {
					fName = strings.TrimSpace(fName)
					if uFlag.Valid && uFlag.Int64 == 0 {
						readOnlyMap[fName] = true
					}
				}
			}
		} else {
			log.Printf("scanRows MetaQuery Error (ignoring): %v", err)
		}
	}

	var cols []domain.Column
	for i, ct := range colTypes {
		name := colNames[i]
		isRO := false
		if readOnlyMap[name] {
			isRO = true
		} else if name == "DB_KEY" || name == "RDB$DB_KEY" {
			isRO = true
		}

		cols = append(cols, domain.Column{
			Name:     name,
			Type:     ct.DatabaseTypeName(),
			ReadOnly: isRO,
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
			log.Printf("scanRows Scan Error: %v", err)
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
	if err := db.QueryRow(query, strings.ToUpper(procName)).Scan(&source); err != nil {
		log.Printf("GetProcedureSource error: %v", err)
		return "", err
	}

	if source.Valid {
		return source.String, nil
	}
	return "", nil
}

func (r *FirebirdRepository) GetProcedureParameters(params domain.ConnectionParams, procName string) ([]domain.ProcedureParameter, error) {
	connStr := r.getConnectionString(params)
	db, err := sql.Open("firebirdsql", connStr)
	if err != nil {
		return nil, err
	}
	defer db.Close()

	// RDB$PARAMETER_TYPE: 0 = Input, 1 = Output
	query := `
		SELECT RDB$PARAMETER_NAME
		FROM RDB$PROCEDURE_PARAMETERS
		WHERE RDB$PROCEDURE_NAME = ?
		AND RDB$PARAMETER_TYPE = 0
		ORDER BY RDB$PARAMETER_NUMBER
	`
	rows, err := db.Query(query, strings.ToUpper(procName))
	if err != nil {
		log.Printf("GetProcedureParameters error: %v", err)
		return nil, err
	}
	defer rows.Close()

	var paramsList []domain.ProcedureParameter
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			return nil, err
		}
		paramsList = append(paramsList, domain.ProcedureParameter{
			Name: strings.TrimSpace(name),
			Type: "STRING", // Defaulting to string for input UI, can be enhanced by joining RDB$FIELDS
		})
	}
	return paramsList, nil
}

func (r *FirebirdRepository) ExecuteProcedure(params domain.ConnectionParams, procName string, inputParams map[string]interface{}) ([]map[string]interface{}, []domain.Column, error) {
	connStr := r.getConnectionString(params)
	db, err := sql.Open("firebirdsql", connStr)
	if err != nil {
		return nil, nil, err
	}
	defer db.Close()

	// 1. Determine execution mode by checking source for "SUSPEND"
	source, err := r.GetProcedureSource(params, procName)
	if err != nil {
		// If fails, default to selectable or try to execute anyway
		log.Printf("ExecuteProcedure: could not get source, proceeding cautiously. Error: %v", err)
	}

	isSelectable := false
	if strings.Contains(strings.ToUpper(source), "SUSPEND") {
		isSelectable = true
	}

	// 2. Fetch parameter order to construct query correctly
	// We need ALL input parameters in order
	// Actually, we need to bind them in order.
	paramOrderQuery := `
		SELECT RDB$PARAMETER_NAME
		FROM RDB$PROCEDURE_PARAMETERS
		WHERE RDB$PROCEDURE_NAME = ?
		AND RDB$PARAMETER_TYPE = 0
		ORDER BY RDB$PARAMETER_NUMBER
	`
	pRows, err := db.Query(paramOrderQuery, strings.ToUpper(procName))
	if err != nil {
		return nil, nil, err
	}
	defer pRows.Close()

	var orderedParams []interface{}
	var paramPlaceholders []string

	for pRows.Next() {
		var pName string
		if err := pRows.Scan(&pName); err != nil {
			return nil, nil, err
		}
		pName = strings.TrimSpace(pName)
		val, ok := inputParams[pName]
		if !ok {
			// Handle missing param? pass null or error?
			// For now pass nil
			orderedParams = append(orderedParams, nil)
		} else {
			orderedParams = append(orderedParams, val)
		}
		paramPlaceholders = append(paramPlaceholders, "?")
	}

	var query string
	if isSelectable {
		query = fmt.Sprintf("SELECT * FROM \"%s\"(%s)", strings.ToUpper(procName), strings.Join(paramPlaceholders, ", "))
	} else {
		query = fmt.Sprintf("EXECUTE PROCEDURE \"%s\"(%s)", strings.ToUpper(procName), strings.Join(paramPlaceholders, ", "))
	}

	log.Printf("ExecuteProcedure Query: %s, Args: %v", query, orderedParams)

	rows, err := db.Query(query, orderedParams...)
	if err != nil {
		log.Printf("ExecuteProcedure DB Error: %v", err)
		return nil, nil, err
	}
	defer rows.Close()

	return r.scanRows(rows, "", db)
}
