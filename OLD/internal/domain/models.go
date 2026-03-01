package domain

// ConnectionParams holds the details required to connect to a Firebird database.
type ConnectionParams struct {
	Database string `json:"database"` // e.g., "localhost:/var/lib/firebird/data/employee.fdb" or "my_alias"
	User     string `json:"user"`
	Password string `json:"password"`
}

// Table represents a database table metadata.
type Table struct {
	Name string `json:"name"`
}

// Column represents a database column metadata.
type Column struct {
	Name     string `json:"name"`
	Type     string `json:"type"`
	ReadOnly bool   `json:"read_only"`
}

// ProcedureParameter represents a stored procedure input parameter.
type ProcedureParameter struct {
	Name string `json:"name"`
	Type string `json:"type"` // Simplified type name
}

// TableMetadata contains full metadata for autocompletion
type TableMetadata struct {
	Name    string   `json:"name"`
	Type    string   `json:"type"` // "TABLE", "VIEW", "PROCEDURE"
	Columns []string `json:"columns"`
}
