from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import unittest
import urllib.parse
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install.py"


class FakeN8nHandler(BaseHTTPRequestHandler):
    workflows: dict[str, dict[str, Any]] = {}
    creates = 0
    updates = 0
    publishes: list[str] = []

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def response(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, Any]:
        size = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(size) or b"{}")

    @staticmethod
    def server_value(payload: dict[str, Any], workflow_id: str, version_id: str) -> dict[str, Any]:
        value = deepcopy(payload)
        for node in value.get("nodes", []):
            if node.get("type") == "n8n-nodes-base.wait":
                node["webhookId"] = f"server-generated-{workflow_id}-{node['id']}"
        return {**value, "id": workflow_id, "versionId": version_id}

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/v1/workflows":
            self.response(404, {"message": "not found"})
            return
        name = urllib.parse.parse_qs(parsed.query).get("name", [""])[0]
        values = [value for value in self.workflows.values() if value.get("name") == name]
        self.response(200, {"data": values, "nextCursor": None})

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path == "/api/v1/workflows":
            payload = self.read_json()
            self.__class__.creates += 1
            workflow_id = f"workflow-{self.creates:02d}"
            value = self.server_value(payload, workflow_id, f"version-{workflow_id}")
            self.workflows[workflow_id] = value
            self.response(200, value)
            return
        if self.path.startswith("/api/v1/workflows/") and self.path.endswith("/publish"):
            workflow_id = self.path.split("/")[4]
            self.read_json()
            if workflow_id not in self.workflows:
                self.response(404, {"message": "not found"})
                return
            self.__class__.publishes.append(workflow_id)
            self.workflows[workflow_id]["active"] = True
            self.workflows[workflow_id]["activeVersionId"] = self.workflows[workflow_id]["versionId"]
            self.response(200, self.workflows[workflow_id])
            return
        self.response(404, {"message": "not found"})

    def do_PUT(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urllib.parse.urlparse(self.path)
        parts = parsed.path.split("/")
        if len(parts) != 5 or parts[:4] != ["", "api", "v1", "workflows"]:
            self.response(404, {"message": "not found"})
            return
        workflow_id = parts[4]
        if workflow_id not in self.workflows:
            self.response(404, {"message": "not found"})
            return
        payload = self.read_json()
        self.__class__.updates += 1
        value = self.server_value(payload, workflow_id, f"updated-{self.updates}")
        self.workflows[workflow_id] = value
        self.response(200, value)


class InstallerIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        FakeN8nHandler.workflows = {}
        FakeN8nHandler.creates = 0
        FakeN8nHandler.updates = 0
        FakeN8nHandler.publishes = []
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeN8nHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def command(self, *extra: str) -> list[str]:
        return [
            sys.executable,
            str(INSTALLER),
            "--n8n-url",
            self.url,
            "--n8n-api-key",
            "test-only-key",
            "--omniroute-url",
            "http://omniroute.internal:20128",
            "--moneyprinter-url",
            "http://moneyprinter.internal:8080",
            "--youtube-channel-id",
            "UCabcdefghijklmnopqrstuv",
            "--omniroute-credential-id",
            "cred-omni",
            "--omniroute-credential-name",
            "RAHASYA OmniRoute",
            "--postgres-credential-id",
            "cred-pg",
            "--postgres-credential-name",
            "RAHASYA PostgreSQL",
            "--youtube-credential-id",
            "cred-youtube",
            "--youtube-credential-name",
            "RAHASYA YouTube",
            "--approval-basic-credential-id",
            "cred-approval",
            "--approval-basic-credential-name",
            "RAHASYA Reviewers",
            *extra,
        ]

    def run_installer(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            self.command(*extra),
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )

    def test_01_creates_resolves_and_selectively_publishes(self) -> None:
        result = self.run_installer("--project-id", "project-1", "--activate", "master,analytics")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(FakeN8nHandler.creates, 19)
        self.assertEqual(FakeN8nHandler.updates, 0)
        self.assertEqual(len(FakeN8nHandler.publishes), 19)
        self.assertTrue(all(value.get("activeVersionId") == value.get("versionId") for value in FakeN8nHandler.workflows.values()))
        self.assertIsNone(re.search(r"__[A-Z0-9_]+__", json.dumps(FakeN8nHandler.workflows)))
        self.assertTrue(all(value.get("projectId") == "project-1" for value in FakeN8nHandler.workflows.values()))

        master = next(value for value in FakeN8nHandler.workflows.values() if value["name"].endswith("Master Production House"))
        execute_ids = [
            node["parameters"]["workflowId"]["value"]
            for node in master["nodes"]
            if node["type"] == "n8n-nodes-base.executeWorkflow"
        ]
        self.assertTrue(execute_ids)
        self.assertTrue(all(value.startswith("workflow-") for value in execute_ids))

    def test_02_second_run_is_idempotent(self) -> None:
        result = self.run_installer("--project-id", "project-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(FakeN8nHandler.creates, 19)
        self.assertEqual(FakeN8nHandler.updates, 0)
        self.assertEqual(result.stdout.count("unchanged"), 19)

    def test_03_current_publications_are_idempotent(self) -> None:
        result = self.run_installer("--project-id", "project-1", "--activate", "master,analytics")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(FakeN8nHandler.publishes), 19)
        self.assertEqual(result.stdout.count("current"), 19)

    def test_04_updates_drifted_definition_without_duplicate(self) -> None:
        first_id = sorted(FakeN8nHandler.workflows)[0]
        FakeN8nHandler.workflows[first_id]["nodes"][0]["name"] = "Drifted Trigger"
        result = self.run_installer("--project-id", "project-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(FakeN8nHandler.creates, 19)
        self.assertEqual(FakeN8nHandler.updates, 1)
        self.assertIn("updated", result.stdout)

    def test_05_rejects_unknown_activation_target(self) -> None:
        result = self.run_installer("--activate", "publisher")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("only master,analytics", result.stderr)

    def test_06_dry_run_reports_equivalence_and_publication_intent(self) -> None:
        result = self.run_installer("--project-id", "project-1", "--dry-run", "--activate", "master")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("DRY RUN unchanged"), 19)
        self.assertIn("DRY RUN publish", result.stdout)
        self.assertEqual(FakeN8nHandler.creates, 19)
        self.assertEqual(FakeN8nHandler.updates, 1)

    def test_07_rejects_invalid_target_channel_id(self) -> None:
        result = self.run_installer("--youtube-channel-id", "not-a-channel")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("24-character YouTube channel ID", result.stderr)

    def test_08_validate_config_does_not_contact_n8n(self) -> None:
        result = self.run_installer(
            "--n8n-url",
            "http://127.0.0.1:1",
            "--validate-config",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("without contacting n8n", result.stdout)

    def test_09_rejects_credentials_embedded_in_service_url(self) -> None:
        result = self.run_installer(
            "--omniroute-url",
            "https://user:password@omniroute.internal",
            "--validate-config",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not contain credentials", result.stderr)
        self.assertNotIn("password", result.stderr)

    def test_10_rejects_malformed_empty_url_port(self) -> None:
        result = self.run_installer(
            "--moneyprinter-url",
            "http://moneyprinter.internal:",
            "--validate-config",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("valid absolute HTTP(S) URL", result.stderr)


if __name__ == "__main__":
    unittest.main()
