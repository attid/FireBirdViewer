# Demo environment

The demo stack runs FireBird Viewer against the bundled Firebird 5 reference
database. It is isolated from other databases and restores its database every
hour.

## Behavior

- Viewer URL: `http://localhost:8080`
- Database: `firebird5:employee`
- User: `demo`
- Password: `demo`
- Reset interval: 3600 seconds
- Firebird port 3050 is available only inside the Compose network.

The connection form is prefilled. Demo mode also enforces the database and user
on the server, so changing form values cannot turn the public viewer into a
proxy for another Firebird server. The regular image remains unrestricted when
`DEMO_MODE` is not enabled.

## Run locally

Build the two images, then start the stack:

```bash
docker build -t ghcr.io/attid/firebirdviewer:latest .
docker build -f demo/Dockerfile -t ghcr.io/attid/firebirdviewer-demo:latest demo
docker compose -f demo/docker-compose.yml up -d
```

The named volume keeps the working database and reset baseline. The reset
container initializes the volume from `demo/employee.fdb`, grants the demo user
access, creates a baseline backup, and periodically restores that baseline.

## Deploy with Portainer

1. Create a new Stack in Portainer.
2. Paste the contents of `demo/docker-compose.yml` into the Web editor.
3. Deploy the stack and wait until `firebird_reset` logs `baseline created`.
4. Open port 8080 on the server, or route a reverse proxy to the viewer service
   on port 5001.

No `.env` file or server-side bind-mounted files are required. Both images are
published to GitHub Container Registry by the repository workflow:

- `ghcr.io/attid/firebirdviewer:latest`
- `ghcr.io/attid/firebirdviewer-demo:latest`

Change the host side of `8080:5001` in the stack when another public port is
needed. Do not publish Firebird port 3050: the credentials are intentionally
public and the database is meant to be reached only through the viewer.

## Reset immediately

Restart only the `firebird_reset` service in Portainer. On startup it restores
the existing baseline before beginning the next hourly interval. To replace the
reference data itself, build and publish a new demo image containing the updated
`demo/employee.fdb`.

