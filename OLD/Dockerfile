# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build Backend
FROM golang:1.24-alpine AS backend-builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
# CGO_ENABLED=0 is important for scratch/alpine mostly, but firebirdsql is pure go.
# We build specifically the main server package.
RUN CGO_ENABLED=0 GOOS=linux go build -o firebird-web-admin ./cmd/server

# Stage 3: Final Image
FROM alpine:latest
ARG VERSION=unknown
LABEL version=$VERSION
WORKDIR /app
# Install ca-certificates just in case we need HTTPS calls later
RUN apk --no-cache add ca-certificates

COPY --from=backend-builder /app/firebird-web-admin .
COPY --from=backend-builder /app/VERSION .
# Copy the built frontend assets from Stage 1 to ./dist in the container
COPY --from=frontend-builder /app/frontend/dist ./dist

EXPOSE 8080
CMD ["./firebird-web-admin"]
