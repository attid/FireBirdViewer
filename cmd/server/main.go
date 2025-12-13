package main

import (
	"firebird-web-admin/internal/repository"
	"firebird-web-admin/internal/service"
	httpHandler "firebird-web-admin/internal/transport/http"
	"os"
	"fmt"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

func main() {
	e := echo.New()

	// Middleware
	e.Use(middleware.Logger())
	e.Use(middleware.Recover())
	e.Use(middleware.CORS())

	// Dependencies
	repo := repository.NewFirebirdRepository()
	svc := service.NewService(repo)
	handler := httpHandler.NewHandler(svc)

	// API Routes
	handler.RegisterRoutes(e)

	if os.Getenv("DEMO_MODE") == "true" {
		fmt.Println("!!! DEMO MODE ENABLED !!!")
		fmt.Println("Only connections to 'firebird5:employee' will be allowed.")
	}

	// Static Files (Frontend)
	// In production, we expect the frontend build to be in ./dist or similar
	cwd, _ := os.Getwd()
	fmt.Printf("Current working directory: %s\n", cwd)

	if _, err := os.Stat("./dist"); err == nil {
		fmt.Println("Serving static files from ./dist")
		// Serve assets explicitly
		e.Static("/assets", "./dist/assets")

		// Serve favicon if exists
		e.File("/favicon.svg", "./dist/favicon.svg")

		// Serve index.html at root
		e.File("/", "./dist/index.html")

		// Handle SPA routing: if file not found, serve index.html
		// Note: This should be last
		e.GET("*", func(c echo.Context) error {
			return c.File("./dist/index.html")
		})
	} else {
		fmt.Println("dist folder not found")
	}

	e.Logger.Fatal(e.Start(":8080"))
}
