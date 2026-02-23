package http

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/labstack/echo/v4"
)

func TestGetConfig(t *testing.T) {
	// Setup
	e := echo.New()
	h := &Handler{}

	// Helper to run request
	runRequest := func() *httptest.ResponseRecorder {
		req := httptest.NewRequest(http.MethodGet, "/api/config", nil)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		_ = h.getConfig(c)
		return rec
	}

	// Backup and restore env and VERSION file
	origDemo := os.Getenv("DEMO_MODE")
	defer os.Setenv("DEMO_MODE", origDemo)

	versionFile := "VERSION"
	var origVersion []byte
	versionExists := false
	if _, err := os.Stat(versionFile); err == nil {
		origVersion, _ = os.ReadFile(versionFile)
		versionExists = true
	}
	defer func() {
		if versionExists {
			_ = os.WriteFile(versionFile, origVersion, 0644)
		} else {
			_ = os.Remove(versionFile)
		}
	}()

	t.Run("DemoModeTrue", func(t *testing.T) {
		os.Setenv("DEMO_MODE", "true")
		_ = os.WriteFile(versionFile, []byte("1.2.3"), 0644)

		rec := runRequest()

		if rec.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", rec.Code)
		}

		var resp map[string]interface{}
		if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
			t.Fatalf("failed to unmarshal response: %v", err)
		}

		if resp["demo"] != true {
			t.Errorf("expected demo true, got %v", resp["demo"])
		}
		if resp["version"] != "1.2.3" {
			t.Errorf("expected version 1.2.3, got %v", resp["version"])
		}
	})

	t.Run("DemoModeFalse", func(t *testing.T) {
		os.Setenv("DEMO_MODE", "false")
		_ = os.WriteFile(versionFile, []byte("0.9.0"), 0644)

		rec := runRequest()

		var resp map[string]interface{}
		_ = json.Unmarshal(rec.Body.Bytes(), &resp)

		if resp["demo"] != false {
			t.Errorf("expected demo false, got %v", resp["demo"])
		}
		if resp["version"] != "0.9.0" {
			t.Errorf("expected version 0.9.0, got %v", resp["version"])
		}
	})

	t.Run("NoVersionFile", func(t *testing.T) {
		_ = os.Remove(versionFile)

		rec := runRequest()

		var resp map[string]interface{}
		_ = json.Unmarshal(rec.Body.Bytes(), &resp)

		if resp["version"] != "unknown" {
			t.Errorf("expected version unknown, got %v", resp["version"])
		}
	})
}
