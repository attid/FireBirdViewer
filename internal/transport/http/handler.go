package http

import (
	"encoding/base64"
	"encoding/json"
	"firebird-web-admin/internal/domain"
	"firebird-web-admin/internal/service"
	"fmt"
	"net/http"
	"strconv"
	"os"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/labstack/echo/v4"
)

type Handler struct {
	svc *service.Service
}

func NewHandler(svc *service.Service) *Handler {
	return &Handler{svc: svc}
}

// JWT Secret (In production this should be in env var)
var jwtSecret = []byte("super-secret-key-change-me")

type Claims struct {
	ConnParams string `json:"conn_params"`
	jwt.RegisteredClaims
}

func (h *Handler) RegisterRoutes(e *echo.Echo) {
	api := e.Group("/api")
	api.GET("/config", h.getConfig)
	api.POST("/connect", h.connect)

	// Protected routes
	api.Use(h.authMiddleware)
	api.GET("/tables", h.listTables)
	api.GET("/views", h.listViews)
	api.GET("/procedures", h.listProcedures)
	api.GET("/procedure/:name/source", h.getProcedureSource)
	api.GET("/table/:name/data", h.getTableData)
	api.PUT("/table/:name/data", h.updateTableData)
}

func (h *Handler) getConfig(c echo.Context) error {
	demo := os.Getenv("DEMO_MODE") == "true"
	versionBytes, _ := os.ReadFile("VERSION")
	version := string(versionBytes)
	if version == "" {
		version = "unknown"
	}
	return c.JSON(http.StatusOK, map[string]interface{}{
		"demo":    demo,
		"version": version,
	})
}

func (h *Handler) connect(c echo.Context) error {
	var params domain.ConnectionParams
	if err := c.Bind(&params); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "Invalid request"})
	}

	if os.Getenv("DEMO_MODE") == "true" {
		if params.Database != "firebird5:employee" {
			fmt.Printf("Blocked connection attempt to %s in DEMO MODE\n", params.Database)
			return c.JSON(http.StatusForbidden, map[string]string{"error": "Demo mode: only firebird5:employee allowed"})
		}
	}

	if err := h.svc.Connect(params); err != nil {
		return c.JSON(http.StatusUnauthorized, map[string]string{"error": "Connection failed: " + err.Error()})
	}

	// Serialize params to store in token
	// Note: In a real app, encrypt this or use a session ID.
	paramsJSON, _ := json.Marshal(params)
	encodedParams := base64.StdEncoding.EncodeToString(paramsJSON)

	claims := &Claims{
		ConnParams: encodedParams,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(24 * time.Hour)),
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	t, err := token.SignedString(jwtSecret)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "Failed to create token"})
	}

	return c.JSON(http.StatusOK, map[string]string{"token": t})
}

func (h *Handler) authMiddleware(next echo.HandlerFunc) echo.HandlerFunc {
	return func(c echo.Context) error {
		authHeader := c.Request().Header.Get("Authorization")
		if authHeader == "" {
			return c.JSON(http.StatusUnauthorized, map[string]string{"error": "Missing token"})
		}

		tokenString := ""
		if len(authHeader) > 7 && authHeader[:7] == "Bearer " {
			tokenString = authHeader[7:]
		} else {
			tokenString = authHeader
		}

		claims := &Claims{}
		token, err := jwt.ParseWithClaims(tokenString, claims, func(token *jwt.Token) (interface{}, error) {
			return jwtSecret, nil
		})

		if err != nil || !token.Valid {
			return c.JSON(http.StatusUnauthorized, map[string]string{"error": "Invalid token"})
		}

		// Decode params
		decodedParamsJSON, err := base64.StdEncoding.DecodeString(claims.ConnParams)
		if err != nil {
			return c.JSON(http.StatusUnauthorized, map[string]string{"error": "Invalid token data"})
		}

		var params domain.ConnectionParams
		if err := json.Unmarshal(decodedParamsJSON, &params); err != nil {
			return c.JSON(http.StatusUnauthorized, map[string]string{"error": "Invalid token data"})
		}

		c.Set("connParams", params)
		return next(c)
	}
}

func (h *Handler) listTables(c echo.Context) error {
	params := c.Get("connParams").(domain.ConnectionParams)
	tables, err := h.svc.ListTables(params)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	return c.JSON(http.StatusOK, tables)
}

func (h *Handler) listViews(c echo.Context) error {
	params := c.Get("connParams").(domain.ConnectionParams)
	tables, err := h.svc.ListViews(params)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	return c.JSON(http.StatusOK, tables)
}

func (h *Handler) listProcedures(c echo.Context) error {
	params := c.Get("connParams").(domain.ConnectionParams)
	tables, err := h.svc.ListProcedures(params)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	return c.JSON(http.StatusOK, tables)
}

func (h *Handler) getProcedureSource(c echo.Context) error {
	params := c.Get("connParams").(domain.ConnectionParams)
	procName := c.Param("name")

	source, err := h.svc.GetProcedureSource(params, procName)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	return c.JSON(http.StatusOK, map[string]string{"source": source})
}

func (h *Handler) getTableData(c echo.Context) error {
	params := c.Get("connParams").(domain.ConnectionParams)
	tableName := c.Param("name")

	// Parse pagination params
	limitStr := c.QueryParam("limit")
	offsetStr := c.QueryParam("offset")
	sortField := c.QueryParam("sortField")
	sortOrder := c.QueryParam("sortOrder")

	limit := 100 // Default
	offset := 0

	if val, err := strconv.Atoi(limitStr); err == nil && val > 0 {
		limit = val
	}
	if val, err := strconv.Atoi(offsetStr); err == nil && val >= 0 {
		offset = val
	}

	data, cols, count, err := h.svc.GetData(params, tableName, limit, offset, sortField, sortOrder)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"data":      data,
		"columns":   cols,
		"total":     count,
		"limit":     limit,
		"offset":    offset,
		"sortField": sortField,
		"sortOrder": sortOrder,
	})
}

type UpdateRequest struct {
	DBKey string                 `json:"db_key"`
	Data  map[string]interface{} `json:"data"`
}

func (h *Handler) updateTableData(c echo.Context) error {
	params := c.Get("connParams").(domain.ConnectionParams)
	tableName := c.Param("name")

	var req UpdateRequest
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "Invalid request body"})
	}

	if req.DBKey == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "Missing db_key"})
	}

	if err := h.svc.UpdateData(params, tableName, req.DBKey, req.Data); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, map[string]string{"status": "success"})
}
