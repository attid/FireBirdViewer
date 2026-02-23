package repository

import (
	"firebird-web-admin/internal/domain"
	"testing"
)

func TestGetConnectionString(t *testing.T) {
	repo := NewFirebirdRepository()

	tests := []struct {
		name     string
		params   domain.ConnectionParams
		expected string
	}{
		{
			name: "Standard host:path",
			params: domain.ConnectionParams{
				User:     "sysdba",
				Password: "password",
				Database: "100.77.235.41:ac",
			},
			expected: "sysdba:password@100.77.235.41/ac",
		},
		{
			name: "Host with custom port host/port:path",
			params: domain.ConnectionParams{
				User:     "sysdba",
				Password: "password",
				Database: "100.77.235.41/3050:ac",
			},
			expected: "sysdba:password@100.77.235.41:3050/ac",
		},
		{
			name: "Localhost path localhost:path",
			params: domain.ConnectionParams{
				User:     "sysdba",
				Password: "password",
				Database: "localhost:C:/db.fdb",
			},
			expected: "sysdba:password@localhost/C:/db.fdb",
		},
		{
			name: "Alias only",
			params: domain.ConnectionParams{
				User:     "sysdba",
				Password: "password",
				Database: "alias",
			},
			expected: "sysdba:password@alias",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := repo.getConnectionString(tt.params)
			if got != tt.expected {
				t.Errorf("getConnectionString() = %v, want %v", got, tt.expected)
			}
		})
	}
}

func TestQuoteIdentifier(t *testing.T) {
	repo := NewFirebirdRepository()

	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "Simple identifier",
			input:    "EMPLOYEE",
			expected: "\"EMPLOYEE\"",
		},
		{
			name:     "Identifier with spaces",
			input:    "My Table",
			expected: "\"My Table\"",
		},
		{
			name:     "Identifier with double quotes",
			input:    "Table\"Name",
			expected: "\"Table\"\"Name\"",
		},
		{
			name:     "Identifier with multiple double quotes",
			input:    "\"Quoted\"",
			expected: "\"\"\"Quoted\"\"\"",
		},
		{
			name:     "Empty identifier",
			input:    "",
			expected: "\"\"",
		},
		{
			name:     "SQL Injection attempt",
			input:    "USERS\"; DROP TABLE STUDENTS; --",
			expected: "\"USERS\"\"; DROP TABLE STUDENTS; --\"",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := repo.quoteIdentifier(tt.input)
			if got != tt.expected {
				t.Errorf("quoteIdentifier(%q) = %v, want %v", tt.input, got, tt.expected)
			}
		})
	}
}

func TestMapFirebirdTypeToSQL(t *testing.T) {
	repo := NewFirebirdRepository()

	tests := []struct {
		name     string
		fType    int
		lenVal   int
		precVal  int
		scaleVal int
		expected string
	}{
		{"Smallint", 7, 0, 0, 0, "SMALLINT"},
		{"Integer", 8, 0, 0, 0, "INTEGER"},
		{"Float", 10, 0, 0, 0, "FLOAT"},
		{"Date", 12, 0, 0, 0, "DATE"},
		{"Time", 13, 0, 0, 0, "TIME"},
		{"Char", 14, 10, 0, 0, "CHAR(10)"},
		{"Decimal", 16, 0, 10, -2, "DECIMAL(10, 2)"},
		{"Bigint", 16, 0, 0, 0, "BIGINT"},
		{"Double", 27, 0, 0, 0, "DOUBLE PRECISION"},
		{"Timestamp", 35, 0, 0, 0, "TIMESTAMP"},
		{"Varchar", 37, 50, 0, 0, "VARCHAR(50)"},
		{"Blob", 261, 0, 0, 0, "BLOB"},
		{"Unknown", 999, 0, 0, 0, "TYPE_999"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := repo.mapFirebirdTypeToSQL(tt.fType, tt.lenVal, tt.precVal, tt.scaleVal)
			if got != tt.expected {
				t.Errorf("mapFirebirdTypeToSQL() = %v, want %v", got, tt.expected)
			}
		})
	}
}
