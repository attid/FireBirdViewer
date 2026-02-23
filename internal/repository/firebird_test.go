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
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := repo.quoteIdentifier(tt.input)
			if got != tt.expected {
				t.Errorf("quoteIdentifier() = %v, want %v", got, tt.expected)
			}
		})
	}
}
