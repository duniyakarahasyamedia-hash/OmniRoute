from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_PATH = ROOT / "scripts" / "deploy.py"
SPEC = importlib.util.spec_from_file_location("rahasya_deploy", DEPLOY_PATH)
assert SPEC and SPEC.loader
DEPLOY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEPLOY)


class DeployUnitTest(unittest.TestCase):
    def test_dotenv_loads_without_overriding_process_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "# comment\nexport N8N_BASE_URL='https://from-file.example'\n"
                'N8N_API_KEY="quoted value" # safe comment\nEMPTY=\n',
                encoding="utf-8",
            )
            environment = {"N8N_BASE_URL": "https://process.example"}
            self.assertTrue(DEPLOY.load_dotenv(path, environment))
            self.assertEqual(environment["N8N_BASE_URL"], "https://process.example")
            self.assertEqual(environment["N8N_API_KEY"], "quoted value")
            self.assertEqual(environment["EMPTY"], "")

    def test_postgres_url_is_removed_from_argv_environment(self) -> None:
        source = {
            "PATH": os.environ.get("PATH", ""),
            "N8N_API_KEY": "not-for-psql",
            "RAHASYA_YOUTUBE_CREDENTIAL_ID": "not-for-psql-either",
            "RAHASYA_DATABASE_URL": (
                "postgresql://runtime%2Duser:do%20not%20print@db.internal:5433/rahasya"
                "?sslmode=require&connect_timeout=9"
            ),
        }
        result = DEPLOY.postgres_environment(source["RAHASYA_DATABASE_URL"], source)
        self.assertNotIn("RAHASYA_DATABASE_URL", result)
        self.assertNotIn("N8N_API_KEY", result)
        self.assertNotIn("RAHASYA_YOUTUBE_CREDENTIAL_ID", result)
        self.assertEqual(result["PGHOST"], "db.internal")
        self.assertEqual(result["PGPORT"], "5433")
        self.assertEqual(result["PGDATABASE"], "rahasya")
        self.assertEqual(result["PGUSER"], "runtime-user")
        self.assertEqual(result["PGPASSWORD"], "do not print")
        self.assertEqual(result["PGSSLMODE"], "require")
        self.assertEqual(result["PGCONNECT_TIMEOUT"], "9")

    def test_database_url_does_not_inherit_ambient_libpq_connection(self) -> None:
        source = {
            "RAHASYA_DATABASE_URL": "postgresql://suite-user@db.internal/rahasya",
            "PGHOST": "wrong.internal",
            "PGPASSWORD": "wrong-password",
            "PGSERVICE": "wrong-service",
            "PGSSLMODE": "disable",
        }
        result = DEPLOY.postgres_environment(source["RAHASYA_DATABASE_URL"], source)
        self.assertEqual(result["PGHOST"], "db.internal")
        self.assertNotIn("PGPASSWORD", result)
        self.assertNotIn("PGSERVICE", result)
        self.assertNotIn("PGSSLMODE", result)

    def test_migration_uses_libpq_environment_not_database_url_argument(self) -> None:
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "RAHASYA_DATABASE_URL": "postgresql://user:secret@db.internal/rahasya",
        }
        completed = subprocess.CompletedProcess(args=[], returncode=0)
        with mock.patch.object(DEPLOY.shutil, "which", return_value="/usr/bin/psql"), mock.patch.object(
            DEPLOY.subprocess, "run", return_value=completed
        ) as run:
            DEPLOY.apply_migration(environment)
        command = run.call_args.args[0]
        child_environment = run.call_args.kwargs["env"]
        self.assertNotIn("secret", " ".join(command))
        self.assertNotIn("RAHASYA_DATABASE_URL", child_environment)
        self.assertEqual(child_environment["PGPASSWORD"], "secret")
        self.assertIn(str(DEPLOY.MIGRATION), command)

    def test_configuration_error_lists_names_not_values(self) -> None:
        with self.assertRaises(DEPLOY.DeploymentError) as caught:
            DEPLOY.require_configuration({"N8N_API_KEY": "sensitive-test-value"}, migration=True)
        message = str(caught.exception)
        self.assertIn("N8N_BASE_URL", message)
        self.assertIn("RAHASYA_DATABASE_URL", message)
        self.assertNotIn("sensitive-test-value", message)

    def test_unsupported_database_query_parameter_is_rejected(self) -> None:
        with self.assertRaises(DEPLOY.DeploymentError):
            DEPLOY.postgres_environment(
                "postgresql://user:pass@db.internal/rahasya?unknown=value", {}
            )


if __name__ == "__main__":
    unittest.main()
