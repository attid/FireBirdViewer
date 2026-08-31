# Demo environment

The public demo runs FireBirdViewer against a bundled Firebird 5 database and
restores it every hour. Users may execute full SQL and DDL. Isolation and
resource controls contain that deliberate privilege.

## Required deployment values

Before deployment, edit the literal placeholder in `demo/docker-compose.yml`:

- `FIREBIRD_ROOT_PASSWORD=replace_with_random_root_password` must be replaced
  in both Firebird services with the same random password.
The Firebird containers intentionally fail startup while the placeholder remains.
Viewer generates its session key automatically and persists it in `viewer_state`.
No `.env` file or Compose variable substitution is required.

## Behavior and boundaries

- URL: `http://localhost:8080`
- Database: `firebird5:employee`
- SQL user: `demo` / `demo`
- Reset interval: 3600 seconds
- Only Traefik publishes a host port.
- Firebird accepts the `employee` alias and rejects raw filesystem paths.
- Viewer runs as UID/GID 10001 with a read-only root filesystem and no Linux
  capabilities.
- Demo SQL defaults: 15 second statement timeout, 1000 returned rows, 2 MiB
  result data, and four concurrent arbitrary-query operations.

The query values are configurable security controls through the literal
`DEMO_QUERY_*` Compose environment entries. They do not apply to normal viewer
deployments.

## Run locally

After replacing the root-password placeholder:

```bash
docker build -t ghcr.io/attid/firebirdviewer:latest .
docker build -f demo/Dockerfile -t ghcr.io/attid/firebirdviewer-demo:latest demo
docker compose -f demo/docker-compose.yml up -d --wait
```

Open `http://localhost:8080`. Use `docker compose -f
demo/docker-compose.yml down` to stop the stack. Add `--volumes` only when the
demo database and reset baseline should also be discarded.

## Deploy with Portainer

Use a Git-backed Portainer stack so the two checked-in Traefik configuration
files are available beside the Compose file. Edit the literal root password in the
stack editor, deploy, and wait for all health checks. Do not publish port 3050
or add a direct viewer port; only the proxy port `8080` is intended to be
public.

The images are published as:

- `ghcr.io/attid/firebirdviewer:latest`
- `ghcr.io/attid/firebirdviewer-demo:latest`

For Internet deployment, terminate TLS at an upstream reverse proxy and
preserve `X-Forwarded-Proto: https`; FireBirdViewer then marks its encrypted
connection cookie `Secure`.

## Reset immediately

Restart only `firebird_reset`. It restores the baseline before waiting for the
next interval. To replace the reference data, build a new demo image containing
the updated `demo/employee.fdb`.

## Verification

Unit and static Compose checks run under `just check`. The Docker-backed test
builds both images, creates a uniquely named disposable stack, verifies alias
and filesystem-path behavior, and removes its test volume afterward:

```bash
just test-integration
```
