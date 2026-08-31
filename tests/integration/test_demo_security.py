"""End-to-end checks for the hardened disposable demo stack."""

import json
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
COMPOSE = ROOT / "demo" / "docker-compose.yml"
PROJECT = "firebirdviewer_security_test"
ROOT_PASSWORD = "integration-root-password-not-for-production"
TEST_HTTP_PORT = 18080


def _docker(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args],
        cwd=ROOT,
        input=input_text,
        text=True,
        check=True,
        capture_output=True,
    )


def test_demo_compose_declares_security_boundaries():
    text = COMPOSE.read_text()

    assert "FIREBIRD_CONF_DatabaseAccess=None" in text
    assert "read_only: true" in text
    assert "cap_drop: [ALL]" in text
    assert "no-new-privileges:true" in text
    assert "internal: true" in text
    assert "./traefik-dynamic.yml" in text
    assert '"8080:8080"' in text
    assert '"8080:5001"' not in text
    assert text.count("DEMO_USER=") == 2


@pytest.mark.skipif(
    os.environ.get("RUN_DOCKER_INTEGRATION") != "1",
    reason="set RUN_DOCKER_INTEGRATION=1 to run the destructive disposable-stack test",
)
def test_demo_alias_readonly_and_container_isolation():
    compose = (
        COMPOSE.read_text()
        .replace("replace_with_random_root_password", ROOT_PASSWORD)
        .replace('"8080:8080"', f'"{TEST_HTTP_PORT}:8080"')
    )
    with tempfile.TemporaryDirectory(prefix="firebirdviewer-security-") as temp_dir:
        compose_file = Path(temp_dir) / "compose.yml"
        compose_file.write_text(compose)
        compose_args = (
            "compose",
            "--project-name",
            PROJECT,
            "--project-directory",
            str(ROOT / "demo"),
            "-f",
            str(compose_file),
        )
        _run_stack_checks(compose_args)


def _run_stack_checks(compose_args: tuple[str, ...]) -> None:
    try:
        _docker("build", "-t", "ghcr.io/attid/firebirdviewer:latest", ".")
        _docker(
            "build",
            "-f",
            "demo/Dockerfile",
            "-t",
            "ghcr.io/attid/firebirdviewer-demo:latest",
            "demo",
        )
        try:
            _docker(*compose_args, "up", "-d", "--wait")
        except subprocess.CalledProcessError as exc:
            logs = subprocess.run(
                ["docker", *compose_args, "logs", "--no-color"],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            raise AssertionError(f"stack startup failed:\n{logs.stdout}\n{logs.stderr}") from exc

        with urllib.request.urlopen(
            f"http://127.0.0.1:{TEST_HTTP_PORT}/healthz", timeout=5
        ) as response:
            assert json.load(response)["status"] == "ok"

        alias = _docker(
            *compose_args,
            "exec",
            "-T",
            "firebird5",
            "isql",
            "-q",
            "-u",
            "SYSDBA",
            "-p",
            ROOT_PASSWORD,
            "localhost:employee",
            input_text="select 1 from rdb$database;\n",
        )
        assert "1" in alias.stdout

        raw_path = subprocess.run(
            [
                "docker",
                *compose_args,
                "exec",
                "-T",
                "firebird5",
                "isql",
                "-q",
                "-u",
                "SYSDBA",
                "-p",
                ROOT_PASSWORD,
                "localhost:/var/lib/firebird/data/employee.fdb",
            ],
            cwd=ROOT,
            input="quit;\n",
            text=True,
            capture_output=True,
        )
        assert raw_path.returncode != 0

        full_ddl = _docker(
            *compose_args,
            "exec",
            "-T",
            "firebird5",
            "isql",
            "-q",
            "-u",
            "demo",
            "-p",
            "demo",
            "localhost:employee",
            input_text=(
                "create table SECURITY_DDL_TEST (ID integer);\n"
                "commit;\ndrop table SECURITY_DDL_TEST;\ncommit;\n"
            ),
        )
        assert "Statement failed" not in full_ddl.stderr

        transaction_guard = _docker(
            *compose_args,
            "exec",
            "-T",
            "viewer",
            "/app/.venv/bin/python",
            "-c",
            (
                "import asyncio; "
                "from src.domain.models import ConnectionParams; "
                "from src.repository.firebird import FirebirdRepository; "
                "repo=FirebirdRepository(ConnectionParams(database='firebird5:employee',"
                "user='demo',password='demo')); "
                "result=asyncio.run(repo.execute_readonly_query("
                "'create table FORBIDDEN_TRANSACTION_DDL (ID integer)')); "
                "assert result.error, result"
            ),
        )
        assert transaction_guard.returncode == 0

        confirmed_ai_ddl = _docker(
            *compose_args,
            "exec",
            "-T",
            "viewer",
            "/app/.venv/bin/python",
            "-c",
            (
                "import asyncio\n"
                "from src.application.use_cases import ExecuteAiDmlUseCase\n"
                "from src.domain.models import ConnectionParams\n"
                "from src.repository.firebird import FirebirdRepository\n"
                "async def check():\n"
                " repo=FirebirdRepository(ConnectionParams(database='firebird5:employee',"
                "user='demo',password='demo'));\n"
                " uc=ExecuteAiDmlUseCase(repo);\n"
                " created=await uc.execute('CREATE TABLE AI_SANDBOX_TEST (ID INTEGER)');\n"
                " assert not created.error, created.error;\n"
                " dropped=await uc.execute('DROP TABLE AI_SANDBOX_TEST');\n"
                " assert not dropped.error, dropped.error;\n"
                " await repo.close()\n"
                "asyncio.run(check())"
            ),
        )
        assert confirmed_ai_ddl.returncode == 0

        viewer_id = _docker(*compose_args, "ps", "-q", "viewer").stdout.strip()
        inspected = json.loads(_docker("inspect", viewer_id).stdout)[0]
        assert inspected["Config"]["User"] == "10001:10001"
        assert inspected["HostConfig"]["ReadonlyRootfs"] is True
        assert "ALL" in inspected["HostConfig"]["CapDrop"]
    finally:
        subprocess.run(
            ["docker", *compose_args, "down", "--volumes", "--remove-orphans"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
