#!/usr/bin/env python3
"""Idempotently install the RAHASYA n8n workflow suite through n8n's public API."""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "manifest.json"


def fail(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Install RAHASYA production-house workflows into n8n")
    p.add_argument("--n8n-url", default=env("N8N_BASE_URL"), help="n8n base URL; or N8N_BASE_URL")
    p.add_argument("--n8n-api-key", default=env("N8N_API_KEY"), help="n8n API key; or N8N_API_KEY")
    p.add_argument("--project-id", default=env("N8N_PROJECT_ID"), help="Optional n8n project ID")
    p.add_argument("--omniroute-url", default=env("OMNIROUTE_BASE_URL", "http://host.docker.internal:20128"))
    p.add_argument("--omniroute-model", default=env("OMNIROUTE_MODEL", "auto"))
    p.add_argument("--omniroute-image-model", default=env("OMNIROUTE_IMAGE_MODEL", "image"))
    p.add_argument("--moneyprinter-url", default=env("MONEYPRINTER_BASE_URL", "http://host.docker.internal:8080"))
    p.add_argument("--youtube-channel-id", default=env("YOUTUBE_CHANNEL_ID"), help="Expected RAHASYA YouTube channel ID (UC…)")
    for slug, label in [
        ("omniroute", "OmniRoute bearer"), ("postgres", "PostgreSQL"),
        ("youtube", "YouTube OAuth2"), ("approval-basic", "approval form Basic Auth"),
    ]:
        key = slug.upper().replace("-", "_")
        p.add_argument(f"--{slug}-credential-id", default=env(f"RAHASYA_{key}_CREDENTIAL_ID"), help=f"n8n {label} credential ID")
        p.add_argument(f"--{slug}-credential-name", default=env(f"RAHASYA_{key}_CREDENTIAL_NAME"), help=f"n8n {label} credential display name")
    p.add_argument("--activate", default="", help="Comma-separated trigger workflows: master,analytics")
    p.add_argument("--validate-only", action="store_true", help="Validate local artifacts without requiring runtime configuration")
    p.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate local artifacts and runtime configuration without contacting n8n",
    )
    p.add_argument("--dry-run", action="store_true", help="Inspect n8n and print create/update plan without changes")
    p.add_argument("--insecure", action="store_true", help="Disable TLS verification (development only)")
    return p


def load_manifest() -> tuple[dict[str, Any], list[tuple[dict[str, Any], dict[str, Any]]]]:
    try:
        manifest = json.loads(MANIFEST_PATH.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read manifest: {exc}")
    entries = []
    names = set()
    for item in manifest.get("workflows", []):
        path = ROOT / item["file"]
        try:
            workflow = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            fail(f"cannot read {path}: {exc}")
        if workflow.get("name") != item.get("name"):
            fail(f"manifest name mismatch in {path.name}")
        if workflow["name"] in names:
            fail(f"duplicate local workflow name: {workflow['name']}")
        names.add(workflow["name"])
        validate_workflow(path, workflow)
        entries.append((item, workflow))
    if not entries:
        fail("manifest contains no workflows")
    return manifest, entries


def validate_workflow(path: Path, workflow: dict[str, Any]) -> None:
    required = {"name", "nodes", "connections", "settings"}
    if not required.issubset(workflow):
        fail(f"{path.name} is missing required n8n fields")
    node_names = [n.get("name") for n in workflow["nodes"]]
    if any(not name for name in node_names) or len(node_names) != len(set(node_names)):
        fail(f"{path.name} has missing or duplicate node names")
    known = set(node_names)
    for source, connection in workflow["connections"].items():
        if source not in known:
            fail(f"{path.name} connection source does not exist: {source}")
        for output in connection.get("main", []):
            for target in output:
                if target.get("node") not in known:
                    fail(f"{path.name} connection target does not exist: {target.get('node')}")
    serialized = json.dumps(workflow)
    forbidden = ["sk-", "ghp_", "AIza", "postgresql://", "Bearer eyJ"]
    if any(value in serialized for value in forbidden):
        fail(f"{path.name} appears to contain a committed secret")


def replace_tree(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        result = value
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result
    if isinstance(value, list):
        return [replace_tree(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: replace_tree(item, replacements) for key, item in value.items()}
    return value


class N8nClient:
    def __init__(self, base_url: str, api_key: str, insecure: bool):
        self.base = base_url.rstrip("/") + "/api/v1"
        self.key = api_key
        self.context = ssl._create_unverified_context() if insecure else None

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            self.base + path,
            data=payload,
            method=method,
            headers={"Accept": "application/json", "Content-Type": "application/json", "X-N8N-API-KEY": self.key},
        )
        try:
            with urllib.request.urlopen(request, context=self.context, timeout=60) as response:
                raw = response.read().decode()
        except urllib.error.HTTPError as exc:
            fail(f"n8n API {method} {path} returned HTTP {exc.code}; inspect sanitized n8n server logs")
        except urllib.error.URLError:
            fail("cannot connect to the configured n8n API")
        try:
            return json.loads(raw or "{}")
        except json.JSONDecodeError:
            fail(f"n8n API {method} {path} returned a non-JSON response")

    def exact_by_name(self, name: str, project_id: str) -> dict[str, Any] | None:
        query: dict[str, Any] = {"name": name, "limit": 100, "excludePinnedData": "true"}
        if project_id:
            query["projectId"] = project_id
        response = self.request("GET", "/workflows?" + urllib.parse.urlencode(query))
        matches = [item for item in response.get("data", []) if item.get("name") == name]
        if len(matches) > 1:
            fail(f"multiple workflows named {name!r}; remove duplicates before installing")
        return matches[0] if matches else None

    def create(self, workflow: dict[str, Any], project_id: str) -> dict[str, Any]:
        body = writable(workflow)
        if project_id:
            body["projectId"] = project_id
        return self.request("POST", "/workflows", body)

    def update(self, workflow_id: str, workflow: dict[str, Any]) -> dict[str, Any]:
        return self.request("PUT", f"/workflows/{urllib.parse.quote(workflow_id)}?publishIfActive=false", writable(workflow))

    def publish(self, workflow_id: str, version_id: str, name: str) -> dict[str, Any]:
        body = {"versionId": version_id, "name": "RAHASYA production suite", "description": f"Published by deterministic installer: {name}"}
        return self.request("POST", f"/workflows/{urllib.parse.quote(workflow_id)}/publish", body)


def writable(workflow: dict[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(workflow[key]) for key in ("name", "nodes", "connections", "settings", "staticData", "pinData") if key in workflow}


def comparable_nodes(nodes: Any) -> Any:
    """Remove node fields generated and owned by n8n itself."""
    result = deepcopy(nodes)
    if isinstance(result, list):
        for node in result:
            if isinstance(node, dict):
                node.pop("webhookId", None)
    return result


def equivalent(existing: dict[str, Any], desired: dict[str, Any]) -> bool:
    if existing.get("name") != desired.get("name"):
        return False
    if comparable_nodes(existing.get("nodes")) != comparable_nodes(desired.get("nodes")):
        return False
    if existing.get("connections") != desired.get("connections"):
        return False
    existing_settings = existing.get("settings") or {}
    return all(existing_settings.get(key) == value for key, value in (desired.get("settings") or {}).items())


def workflow_dependencies(workflow: dict[str, Any], id_to_name: dict[str, str]) -> list[str]:
    dependencies: list[str] = []
    for node in workflow.get("nodes", []):
        if node.get("type") != "n8n-nodes-base.executeWorkflow":
            continue
        workflow_id = node.get("parameters", {}).get("workflowId", {})
        value = workflow_id.get("value") if isinstance(workflow_id, dict) else workflow_id
        dependency = id_to_name.get(str(value))
        if dependency and dependency not in dependencies:
            dependencies.append(dependency)
    return dependencies


def publication_order(
    targets: list[str], desired_by_name: dict[str, dict[str, Any]], installed: dict[str, dict[str, Any]]
) -> list[str]:
    id_to_name = {str(result["id"]): name for name, result in installed.items()}
    state: dict[str, str] = {}
    order: list[str] = []

    def visit(name: str) -> None:
        if state.get(name) == "done":
            return
        if state.get(name) == "visiting":
            fail(f"workflow dependency cycle detected at {name}")
        state[name] = "visiting"
        for dependency in workflow_dependencies(desired_by_name[name], id_to_name):
            visit(dependency)
        state[name] = "done"
        order.append(name)

    for target in targets:
        visit(target)
    return order


def validate_base_url(flag: str, value: str) -> None:
    try:
        parsed = urllib.parse.urlparse(value)
        port = parsed.port
    except ValueError:
        fail(f"{flag} must be a valid absolute HTTP(S) URL")
    authority = parsed.netloc.rsplit("@", 1)[-1]
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or authority.endswith(":")
        or any(char.isspace() for char in value)
        or (port is not None and not 1 <= port <= 65535)
    ):
        fail(f"{flag} must be a valid absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        fail(f"{flag} must not contain credentials; use an n8n credential instead")
    if parsed.query or parsed.fragment:
        fail(f"{flag} must not contain a query string or fragment")


def require_runtime_args(args: argparse.Namespace) -> None:
    required = {
        "--n8n-url": args.n8n_url,
        "--n8n-api-key": args.n8n_api_key,
        "--omniroute-url": args.omniroute_url,
        "--omniroute-model": args.omniroute_model,
        "--omniroute-image-model": args.omniroute_image_model,
        "--moneyprinter-url": args.moneyprinter_url,
        "--youtube-channel-id": args.youtube_channel_id,
        "--omniroute-credential-id": args.omniroute_credential_id,
        "--omniroute-credential-name": args.omniroute_credential_name,
        "--postgres-credential-id": args.postgres_credential_id,
        "--postgres-credential-name": args.postgres_credential_name,
        "--youtube-credential-id": args.youtube_credential_id,
        "--youtube-credential-name": args.youtube_credential_name,
        "--approval-basic-credential-id": args.approval_basic_credential_id,
        "--approval-basic-credential-name": args.approval_basic_credential_name,
    }
    missing = [flag for flag, value in required.items() if not value]
    if missing:
        fail("missing required configuration: " + ", ".join(missing))
    if not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", args.youtube_channel_id):
        fail("--youtube-channel-id must be a 24-character YouTube channel ID beginning with UC")
    for flag, value in [
        ("--n8n-url", args.n8n_url),
        ("--omniroute-url", args.omniroute_url),
        ("--moneyprinter-url", args.moneyprinter_url),
    ]:
        validate_base_url(flag, value)


def main() -> None:
    args = parser().parse_args()
    _, entries = load_manifest()
    print(f"Validated {len(entries)} local workflow definitions.")
    if args.validate_only:
        return
    require_runtime_args(args)
    activate = {part.strip() for part in args.activate.split(",") if part.strip()}
    unknown = activate - {"master", "analytics"}
    if unknown:
        fail("--activate accepts only master,analytics")
    if args.validate_config:
        print("Validated installer runtime configuration without contacting n8n.")
        return
    client = N8nClient(args.n8n_url, args.n8n_api_key, args.insecure)
    existing_by_name: dict[str, dict[str, Any] | None] = {}
    for _, workflow in entries:
        existing_by_name[workflow["name"]] = client.exact_by_name(workflow["name"], args.project_id)
    credential_replacements = {
        "__OMNIROUTE_BASE_URL__": args.omniroute_url.rstrip("/"),
        "__OMNIROUTE_MODEL__": args.omniroute_model,
        "__OMNIROUTE_IMAGE_MODEL__": args.omniroute_image_model,
        "__MONEYPRINTER_BASE_URL__": args.moneyprinter_url.rstrip("/"),
        "__YOUTUBE_CHANNEL_ID__": args.youtube_channel_id,
        "__OMNIROUTE_CREDENTIAL_ID__": args.omniroute_credential_id,
        "__OMNIROUTE_CREDENTIAL_NAME__": args.omniroute_credential_name,
        "__POSTGRES_CREDENTIAL_ID__": args.postgres_credential_id,
        "__POSTGRES_CREDENTIAL_NAME__": args.postgres_credential_name,
        "__YOUTUBE_CREDENTIAL_ID__": args.youtube_credential_id,
        "__YOUTUBE_CREDENTIAL_NAME__": args.youtube_credential_name,
        "__APPROVAL_BASIC_CREDENTIAL_ID__": args.approval_basic_credential_id,
        "__APPROVAL_BASIC_CREDENTIAL_NAME__": args.approval_basic_credential_name,
    }
    if args.dry_run:
        existing_ids = {
            key: str(existing_by_name[name]["id"])
            for key, name in WORKFLOW_NAMES.items()
            if existing_by_name.get(name) and existing_by_name[name].get("id")
        }
        workflow_replacements = {f"__WORKFLOW_{key.upper()}_ID__": value for key, value in existing_ids.items()}
        for _, workflow in entries:
            existing = existing_by_name[workflow["name"]]
            desired = replace_tree(workflow, {**credential_replacements, **workflow_replacements})
            action = "create" if not existing else ("unchanged" if equivalent(existing, desired) else "update")
            print(f"DRY RUN {action:9} {workflow['name']}")
        for key in ("master", "analytics"):
            if key in activate:
                print(f"DRY RUN publish   {WORKFLOW_NAMES[key]} (plus dependencies)")
        return

    ids: dict[str, str] = {}
    # Manifest order guarantees all child workflow IDs exist before parent definitions are patched.
    installed: dict[str, dict[str, Any]] = {}
    desired_by_name: dict[str, dict[str, Any]] = {}
    for item, source in entries:
        workflow_replacements = {f"__WORKFLOW_{key.upper()}_ID__": value for key, value in ids.items()}
        desired = replace_tree(source, {**credential_replacements, **workflow_replacements})
        unresolved = sorted(set(re.findall(r"__[A-Z0-9_]+__", json.dumps(desired))))
        if unresolved:
            fail(f"{source['name']} has unresolved placeholders: {', '.join(unresolved)}")
        desired_by_name[source["name"]] = desired
        existing = existing_by_name[source["name"]]
        if existing and equivalent(existing, desired):
            result = existing
            print(f"unchanged {source['name']}")
        elif existing:
            result = client.update(str(existing["id"]), desired)
            print(f"updated   {source['name']}")
        else:
            result = client.create(desired, args.project_id)
            print(f"created   {source['name']}")
        workflow_id = str(result.get("id") or "")
        if not workflow_id:
            fail(f"n8n did not return an ID for {source['name']}")
        key = next((k for k, name in WORKFLOW_NAMES.items() if name == source["name"]), None)
        if key:
            ids[key] = workflow_id
        installed[source["name"]] = result

    activation_names = {WORKFLOW_NAMES[key] for key in activate}
    activation_targets = [workflow["name"] for _, workflow in entries if workflow["name"] in activation_names]
    publish_order = publication_order(activation_targets, desired_by_name, installed)
    for name in publish_order:
        result = installed[name]
        version_id = str(result.get("versionId") or "")
        if not version_id:
            fail(f"n8n did not return a versionId for {name}")
        if str(result.get("activeVersionId") or "") == version_id:
            print(f"current   {name}")
            continue
        installed[name] = client.publish(str(result["id"]), version_id, name)
        reason = "trigger" if name in activation_names else "dependency"
        print(f"published {name} ({reason})")

    for name, desired in desired_by_name.items():
        current = client.exact_by_name(name, args.project_id)
        if not current or not equivalent(current, desired):
            fail(f"post-install verification found definition drift in {name}")
        if re.search(r"__[A-Z0-9_]+__", json.dumps(current)):
            fail(f"post-install verification found an unresolved placeholder in {name}")
        if name in publish_order and str(current.get("activeVersionId") or "") != str(current.get("versionId") or ""):
            fail(f"post-install verification found a non-current publication for {name}")
    print(f"Verified {len(desired_by_name)} installed workflow definitions.")
    print("Installation complete.")


# Duplicated here intentionally so installer remains standalone and does not import generator side effects.
WORKFLOW_NAMES = {
    "preflight": "RAHASYA | 00 Infrastructure Readiness",
    "state": "RAHASYA | 01 State & Cost Ledger", "strategy": "RAHASYA | 02 Trends & Growth Strategist",
    "producer": "RAHASYA | 03 Executive Producer", "research": "RAHASYA | 04 Investigative Researcher",
    "facts": "RAHASYA | 05 Fact Checker", "writer": "RAHASYA | 06 Documentary Writer",
    "retention": "RAHASYA | 07 Retention Editor", "director": "RAHASYA | 08 Director",
    "visuals": "RAHASYA | 09 Cinematographer & Visual Evidence", "rights": "RAHASYA | 10 Rights & Provenance",
    "voice": "RAHASYA | 11 Voice & Sound Director", "render": "RAHASYA | 12 MoneyPrinterTurbo Renderer",
    "packaging": "RAHASYA | 13 Packaging, SEO & Thumbnail", "compliance": "RAHASYA | 14 Compliance Editor",
    "approval": "RAHASYA | 15 Human Approval Gate", "publish": "RAHASYA | 16 YouTube Publisher",
    "master": "RAHASYA | 20 Master Production House", "analytics": "RAHASYA | 30 Analytics & Growth Loop",
}

if __name__ == "__main__":
    main()
