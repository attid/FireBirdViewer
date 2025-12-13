# FireBirdViewer

Lightweight web-based administrator for Firebird SQL databases.

## Features

- **Quick Connect:** Connect to any Firebird database using Host, Path, User, and Password without saving credentials.
- **Table Viewer:** Browse tables and view data.
- **Virtual Scrolling:** Efficiently view large datasets with lazy loading.
- **Modern UI:** Built with Vue 3, PrimeVue, and Tailwind CSS.
- **Dockerized:** Easy to deploy single-container application.
- **Firebird Support:** Targeted for Firebird 4.0 and 5.0+ (ODS 13+).

## Getting Started

### Prerequisites

- Docker
- *Or for local dev:* Go 1.24+ and Node.js 20+

### Running with Docker

```bash
docker pull ghcr.io/attid/firebirdviewer:latest
```
or build and run

```bash
docker build -t firebirdviewer .
docker run -p 8080:8080 firebirdviewer
```
Access the application at `http://localhost:8080`.

### Local Development

1.  **Backend:**
    ```bash
    go run ./cmd/server
    ```

2.  **Frontend:**
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

## Roadmap

See [PLAN.md](PLAN.md) for the development roadmap.
