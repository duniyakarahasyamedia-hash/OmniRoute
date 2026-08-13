#!/usr/bin/env python3
"""Run the complete, repeatable RAHASYA validation, migration, and n8n deployment."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "001_rahasya_production.sql"


class DeploymentError(Exception):
    """An operator-actionable deployment failure with no secret values."""


def fail(message: str) -> NoReturn:
    print(f"deployment error: {message}", file=sys.stderr)
    raise SystemExit(1)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Validate, migrate, install, verify, and optionally publish the RAHASYA n8n suite"
    )
    result.add_argument(
        "--env-file",
        type=Path,
        default=ROOT / ".env",
        help="dotenv configuration (default: automations/rahasya-global/.env); process variables take precedence",
    )
    result.add_argument(
        "--activate",
        default="",
        help="Comma-separated trigger workflows to publish after installation: master,analytics",
    )
    result.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate everything and inspect n8n changes without migrating, writing, or publishing",
    )
    result.add_argument(
        "--skip-migration",
        action="store_true",
        help="Skip PostgreSQL migration only when it was applied independently",
    )
    result.add_argument("--skip-tests", action="store_true", help="Skip the local mocked API test suite")
    result.add_argument("--insecure", action="store_true", help="Forward n8n TLS bypass for disposable local development")
    return result


def load_dotenv(path: Path, environment: dict[str, str]) -> bool:
    """Load a small, strict dotenv subset without overriding process variables."""
    if not path.exists():
        return False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DeploymentError(f"cannot read env file {path}: {exc}") from exc
    for line_number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise DeploymentError(f"invalid dotenv assignment at line {line_number}")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or not (key[0].isalpha() or key[0] == "_") or not all(
            char.isalnum() or char == "_" for char in key
        ):
            raise DeploymentError(f"invalid dotenv variable name at line {line_number}")
        value = value.strip()
        if value.startswith(("'", '"')):
            try:
                parsed = shlex.split(value, comments=True, posix=True)
            except ValueError as exc:
                raise DeploymentError(f"invalid quoted dotenv value at line {line_number}") from exc
            if len(parsed) != 1:
                raise DeploymentError(f"invalid quoted dotenv value at line {line_number}")
            value = parsed[0]
        environment.setdefault(key, value)
    return True


def require_configuration(environment: dict[str, str], *, migration: bool) -> None:
    required = [
        "N8N_BASE_URL",
        "N8N_API_KEY",
        "OMNIROUTE_BASE_URL",
        "OMNIROUTE_MODEL",
        "OMNIROUTE_IMAGE_MODEL",
        "MONEYPRINTER_BASE_URL",
        "YOUTUBE_CHANNEL_ID",
        "RAHASYA_OMNIROUTE_CREDENTIAL_ID",
        "RAHASYA_OMNIROUTE_CREDENTIAL_NAME",
        "RAHASYA_POSTGRES_CREDENTIAL_ID",
        "RAHASYA_POSTGRES_CREDENTIAL_NAME",
        "RAHASYA_YOUTUBE_CREDENTIAL_ID",
        "RAHASYA_YOUTUBE_CREDENTIAL_NAME",
        "RAHASYA_APPROVAL_BASIC_CREDENTIAL_ID",
        "RAHASYA_APPROVAL_BASIC_CREDENTIAL_NAME",
    ]
    if migration:
        required.append("RAHASYA_DATABASE_URL")
    missing = [name for name in required if not environment.get(name, "").strip()]
    if missing:
        raise DeploymentError("missing required environment variables: " + ", ".join(missing))


def postgres_environment(database_url: str, environment: dict[str, str]) -> dict[str, str]:
    """Convert a PostgreSQL URL to libpq environment variables, keeping it out of argv."""
    try:
        parsed = urllib.parse.urlparse(database_url)
        port = parsed.port
    except ValueError as exc:
        raise DeploymentError("RAHASYA_DATABASE_URL is not a valid PostgreSQL URL") from exc
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.params or parsed.fragment:
        raise DeploymentError("RAHASYA_DATABASE_URL must use the postgres:// or postgresql:// scheme")
    database = urllib.parse.unquote(parsed.path.lstrip("/"))
    if not database:
        raise DeploymentError("RAHASYA_DATABASE_URL must include a database name")

    result = dict(environment)
    for key in list(result):
        if key == "N8N_API_KEY" or key.startswith("RAHASYA_"):
            result.pop(key, None)
    mappings = {
        "PGHOST": parsed.hostname,
        "PGPORT": str(port) if port is not None else None,
        "PGDATABASE": database,
        "PGUSER": urllib.parse.unquote(parsed.username) if parsed.username else None,
        "PGPASSWORD": urllib.parse.unquote(parsed.password) if parsed.password else None,
    }
    query_mappings = {
        "application_name": "PGAPPNAME",
        "channel_binding": "PGCHANNELBINDING",
        "connect_timeout": "PGCONNECT_TIMEOUT",
        "options": "PGOPTIONS",
        "sslcert": "PGSSLCERT",
        "sslkey": "PGSSLKEY",
        "sslmode": "PGSSLMODE",
        "sslrootcert": "PGSSLROOTCERT",
        "target_session_attrs": "PGTARGETSESSIONATTRS",
    }
    # The URL is authoritative. Do not silently mix it with inherited libpq settings
    # for another database or with an ambient service/passfile configuration.
    for key in {*mappings, *query_mappings.values(), "PGSERVICE", "PGSERVICEFILE", "PGPASSFILE"}:
        result.pop(key, None)
    for key, value in mappings.items():
        if value is not None:
            result[key] = value

    try:
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise DeploymentError("RAHASYA_DATABASE_URL has malformed connection parameters") from exc
    unsupported = sorted(set(query) - set(query_mappings))
    if unsupported:
        raise DeploymentError(
            "RAHASYA_DATABASE_URL has unsupported connection parameters: " + ", ".join(unsupported)
        )
    for key, values in query.items():
        if len(values) != 1:
            raise DeploymentError(f"RAHASYA_DATABASE_URL repeats connection parameter {key}")
        result[query_mappings[key]] = values[0]
    return result


def run_step(label: str, command: list[str], environment: dict[str, str]) -> None:
    print(f"==> {label}", flush=True)
    try:
        completed = subprocess.run(command, cwd=ROOT, env=environment, check=False)
    except OSError as exc:
        raise DeploymentError(f"could not start {label}: {exc}") from exc
    if completed.returncode != 0:
        raise DeploymentError(f"{label} failed with exit code {completed.returncode}")


def apply_migration(environment: dict[str, str]) -> None:
    psql_name = environment.get("PSQL_BIN", "psql")
    psql = shutil.which(psql_name, path=environment.get("PATH"))
    if not psql:
        raise DeploymentError(
            "psql was not found; install the PostgreSQL client or use --skip-migration only after applying the migration independently"
        )
    pg_environment = postgres_environment(environment["RAHASYA_DATABASE_URL"], environment)
    run_step(
        "Apply transactional PostgreSQL migration",
        [psql, "--set", "ON_ERROR_STOP=1", "--file", str(MIGRATION)],
        pg_environment,
    )


def main() -> int:
    args = parser().parse_args()
    environment = dict(os.environ)
    try:
        loaded = load_dotenv(args.env_file.expanduser().resolve(), environment)
        if loaded:
            print(f"Loaded deployment configuration from {args.env_file}")
        else:
            print(f"No env file found at {args.env_file}; using process environment")
        migrate = not args.skip_migration and not args.dry_run
        require_configuration(environment, migration=migrate)

        # Keep the database URL out of every child except psql, and only expose
        # the n8n API key to installer subprocesses that actually need it.
        installer_environment = dict(environment)
        installer_environment.pop("RAHASYA_DATABASE_URL", None)
        local_environment = dict(installer_environment)
        local_environment.pop("N8N_API_KEY", None)

        python = sys.executable
        run_step(
            "Regenerate deterministic workflow artifacts",
            [python, "scripts/generate_workflows.py"],
            local_environment,
        )
        run_step(
            "Validate workflow and migration controls",
            [python, "scripts/validate.py"],
            local_environment,
        )
        run_step(
            "Validate installer inputs and local artifacts",
            [python, "scripts/install.py", "--validate-config"],
            installer_environment,
        )
        if not args.skip_tests:
            run_step(
                "Run mocked n8n API integration tests",
                [python, "-m", "unittest", "discover", "-s", "tests", "-v"],
                local_environment,
            )
        if migrate:
            apply_migration(environment)
        elif args.dry_run:
            print("==> PostgreSQL migration skipped in dry-run mode")
        else:
            print("==> PostgreSQL migration skipped by operator request")

        installer = [python, "scripts/install.py"]
        if args.activate:
            installer.extend(["--activate", args.activate])
        if args.dry_run:
            installer.append("--dry-run")
        if args.insecure:
            installer.append("--insecure")
        run_step(
            "Inspect n8n deployment" if args.dry_run else "Install and verify n8n workflows",
            installer,
            installer_environment,
        )
    except DeploymentError as exc:
        fail(str(exc))

    if args.dry_run:
        print("Deployment dry run complete; no migration, workflow write, or publication was performed.")
    else:
        publication = args.activate or "none"
        print(f"Deployment complete; requested trigger publication: {publication}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
