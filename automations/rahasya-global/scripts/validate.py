#!/usr/bin/env python3
"""Deterministic structural and security checks for the RAHASYA n8n suite."""

from __future__ import annotations

import json
import re
import sys
from collections import deque
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "manifest.json"
MIGRATION_PATH = ROOT / "migrations" / "001_rahasya_production.sql"
EXPECTED_FILES = [
    "workflows/00-infrastructure-readiness.json",
    "workflows/01-state-cost-ledger.json",
    "workflows/02-strategy.json",
    "workflows/03-producer.json",
    "workflows/04-research.json",
    "workflows/05-facts.json",
    "workflows/06-writer.json",
    "workflows/07-retention.json",
    "workflows/08-director.json",
    "workflows/09-visuals.json",
    "workflows/10-rights.json",
    "workflows/11-voice.json",
    "workflows/12-render-moneyprinterturbo.json",
    "workflows/13-packaging-seo-thumbnail.json",
    "workflows/14-compliance.json",
    "workflows/15-human-approval-gate.json",
    "workflows/16-youtube-publisher.json",
    "workflows/20-master-production-house.json",
    "workflows/30-analytics-growth-loop.json",
]
ALLOWED_PLACEHOLDERS = {
    "__OMNIROUTE_BASE_URL__",
    "__OMNIROUTE_MODEL__",
    "__OMNIROUTE_IMAGE_MODEL__",
    "__MONEYPRINTER_BASE_URL__",
    "__YOUTUBE_CHANNEL_ID__",
    "__OMNIROUTE_CREDENTIAL_ID__",
    "__OMNIROUTE_CREDENTIAL_NAME__",
    "__POSTGRES_CREDENTIAL_ID__",
    "__POSTGRES_CREDENTIAL_NAME__",
    "__YOUTUBE_CREDENTIAL_ID__",
    "__YOUTUBE_CREDENTIAL_NAME__",
    "__APPROVAL_BASIC_CREDENTIAL_ID__",
    "__APPROVAL_BASIC_CREDENTIAL_NAME__",
}
EXPECTED_GATES = [
    "concept",
    "research_facts",
    "script",
    "production_rights",
    "final_cut_packaging",
    "disclosure_privacy",
]
TRIGGER_TYPES = {
    "n8n-nodes-base.executeWorkflowTrigger",
    "n8n-nodes-base.formTrigger",
    "n8n-nodes-base.scheduleTrigger",
    "n8n-nodes-base.manualTrigger",
}
SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}"),
    re.compile(r"postgres(?:ql)?://[^\s\"']+", re.I),
    re.compile(r"Bearer\s+eyJ[A-Za-z0-9_-]+", re.I),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


class ValidationError(Exception):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot parse {path.relative_to(ROOT)}: {exc}") from exc


def node_by_name(workflow: dict[str, Any], name: str) -> dict[str, Any]:
    matches = [node for node in workflow["nodes"] if node.get("name") == name]
    check(len(matches) == 1, f"{workflow['name']}: expected exactly one node named {name!r}")
    return matches[0]


def targets(workflow: dict[str, Any], source: str) -> list[str]:
    result: list[str] = []
    connection = workflow.get("connections", {}).get(source, {})
    for channel_outputs in connection.values():
        check(isinstance(channel_outputs, list), f"{workflow['name']}: malformed outputs for {source}")
        for output in channel_outputs:
            check(isinstance(output, list), f"{workflow['name']}: malformed output branch for {source}")
            for edge in output:
                check(isinstance(edge, dict), f"{workflow['name']}: malformed edge for {source}")
                if isinstance(edge.get("node"), str):
                    result.append(edge["node"])
    return result


def validate_graph(workflow: dict[str, Any], node_ids: set[str]) -> None:
    name = workflow.get("name", "<unnamed>")
    nodes = workflow.get("nodes")
    check(isinstance(nodes, list) and nodes, f"{name}: nodes must be a non-empty list")
    names = [node.get("name") for node in nodes]
    check(all(isinstance(value, str) and value for value in names), f"{name}: every node needs a name")
    check(len(names) == len(set(names)), f"{name}: duplicate node name")
    ids = [node.get("id") for node in nodes]
    check(all(isinstance(value, str) and value for value in ids), f"{name}: every node needs an ID")
    check(len(ids) == len(set(ids)), f"{name}: duplicate node ID")
    overlap = node_ids.intersection(ids)
    check(not overlap, f"{name}: node IDs reused across workflows: {sorted(overlap)}")
    node_ids.update(ids)
    known = set(names)
    connections = workflow.get("connections")
    check(isinstance(connections, dict), f"{name}: connections must be an object")
    for source in connections:
        check(source in known, f"{name}: unknown connection source {source!r}")
        for target in targets(workflow, source):
            check(target in known, f"{name}: unknown connection target {target!r}")

    roots = [node["name"] for node in nodes if node.get("type") in TRIGGER_TYPES]
    check(bool(roots), f"{name}: workflow has no supported trigger")
    visited: set[str] = set()
    queue = deque(roots)
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        queue.extend(targets(workflow, current))
    check(visited == known, f"{name}: unreachable nodes: {sorted(known - visited)}")

    for node in nodes:
        check(isinstance(node.get("position"), list) and len(node["position"]) == 2, f"{name}: invalid position")
        check(isinstance(node.get("parameters"), dict), f"{name}: {node['name']} has no parameter object")
        check(node.get("typeVersion") is not None, f"{name}: {node['name']} has no typeVersion")


def validate_credentials(workflow: dict[str, Any]) -> None:
    expected = {
        "httpBearerAuth": ("__OMNIROUTE_CREDENTIAL_ID__", "__OMNIROUTE_CREDENTIAL_NAME__"),
        "postgres": ("__POSTGRES_CREDENTIAL_ID__", "__POSTGRES_CREDENTIAL_NAME__"),
        "youTubeOAuth2Api": ("__YOUTUBE_CREDENTIAL_ID__", "__YOUTUBE_CREDENTIAL_NAME__"),
        "httpBasicAuth": ("__APPROVAL_BASIC_CREDENTIAL_ID__", "__APPROVAL_BASIC_CREDENTIAL_NAME__"),
    }
    for node in workflow["nodes"]:
        credentials = node.get("credentials") or {}
        check(isinstance(credentials, dict), f"{workflow['name']}: malformed credentials on {node['name']}")
        for credential_type, value in credentials.items():
            check(credential_type in expected, f"{workflow['name']}: unexpected credential type {credential_type}")
            check(isinstance(value, dict), f"{workflow['name']}: malformed {credential_type} credential")
            check(
                (value.get("id"), value.get("name")) == expected[credential_type],
                f"{workflow['name']}: committed or incorrect {credential_type} credential metadata",
            )


def validate_http_nodes(workflow: dict[str, Any]) -> None:
    for node in workflow["nodes"]:
        if node.get("type") != "n8n-nodes-base.httpRequest":
            continue
        params = node["parameters"]
        url = str(params.get("url", ""))
        check(url, f"{workflow['name']}: {node['name']} has no URL")
        check("localhost" not in url and "127.0.0.1" not in url, f"{workflow['name']}: local URL committed in {node['name']}")
        method = str(params.get("method", "GET")).upper()
        if params.get("sendBody") and params.get("contentType") == "json":
            check(params.get("specifyBody") == "json", f"{workflow['name']}: {node['name']} must use JSON body mode")
            check("jsonBody" in params, f"{workflow['name']}: {node['name']} has no jsonBody")
        if "__OMNIROUTE_BASE_URL__" in url:
            credentials = node.get("credentials", {})
            check("httpBearerAuth" in credentials, f"{workflow['name']}: OmniRoute request lacks bearer credential")
            response = params.get("options", {}).get("response", {}).get("response", {})
            check(response.get("fullResponse") is True, f"{workflow['name']}: OmniRoute request must preserve telemetry headers")
        if "googleapis.com" in url:
            check("youTubeOAuth2Api" in node.get("credentials", {}), f"{workflow['name']}: YouTube API request lacks OAuth")


def validate_suite(workflows: dict[str, dict[str, Any]]) -> None:
    preflight = workflows["workflows/00-infrastructure-readiness.json"]
    master = workflows["workflows/20-master-production-house.json"]
    approval = workflows["workflows/15-human-approval-gate.json"]
    renderer = workflows["workflows/12-render-moneyprinterturbo.json"]
    publisher = workflows["workflows/16-youtube-publisher.json"]
    analytics = workflows["workflows/30-analytics-growth-loop.json"]
    state = workflows["workflows/01-state-cost-ledger.json"]

    form = node_by_name(master, "Authenticated Production Brief")
    check(form["parameters"].get("authentication") == "n8nUserAuth", "master intake must use n8n user authentication")
    check(form["parameters"].get("requireExecuteAccess") is True, "master intake must require execute access")
    check(form["parameters"].get("options", {}).get("path") == "rahasya-production-brief", "master form path changed")
    check(master.get("settings", {}).get("timezone") == "America/New_York", "master timezone must be America/New_York")
    check(master.get("settings", {}).get("saveExecutionProgress") is True, "master must save execution progress across approvals")
    check(
        targets(master, "Initialize Production Project") == ["Run Infrastructure Readiness"],
        "master must run infrastructure readiness before production work",
    )

    preflight_text = json.dumps(preflight, sort_keys=True)
    for value in [
        "rahasya_projects",
        "configuredOnly=true",
        "/v1/images/generations?configuredOnly=true",
        "/api/v1/tasks",
        "__YOUTUBE_CHANNEL_ID__",
        "PostgreSQL migration is incomplete",
    ]:
        check(value in preflight_text, f"infrastructure readiness is missing {value!r}")
    check(
        targets(preflight, "Verify YouTube OAuth Channel") == ["Enforce Infrastructure Readiness"],
        "infrastructure readiness must fail closed after its service checks",
    )

    master_text = json.dumps(master, sort_keys=True)
    gate_positions = [master_text.find(f'\\"{gate}\\"') for gate in EXPECTED_GATES]
    check(all(position >= 0 for position in gate_positions), "master does not contain all mandatory gates")
    check(master_text.count("__WORKFLOW_APPROVAL_ID__") == 6, "master must execute six approval gates")
    for key in ["preflight", "state", "strategy", "producer", "research", "facts", "writer", "retention", "director", "visuals", "rights", "voice", "render", "packaging", "compliance", "approval", "publish"]:
        ALLOWED_PLACEHOLDERS.add(f"__WORKFLOW_{key.upper()}_ID__")

    wait = node_by_name(approval, "Wait for Authorized Review")
    check(wait["parameters"].get("incomingAuthentication") == "basicAuth", "approval form must require Basic Auth")
    check("httpBasicAuth" in wait.get("credentials", {}), "approval wait node lacks Basic Auth credential")
    approval_text = json.dumps(approval, sort_keys=True)
    for value in ["reviewer=NULL", "notes=NULL", "release_controls='{}'::jsonb", "delete project.release"]:
        check(value in approval_text, f"approval pending reset is missing {value!r}")
    for value in ["Final release privacy status is required", "Final synthetic-media declaration is required", "scheduled publication requires Privacy Status = private"]:
        check(value in approval_text, f"approval release validation is missing {value!r}")

    renderer_text = json.dumps(renderer, sort_keys=True)
    for value in ["Fetch Material Provenance", "material_sources", "source_page", "publication is blocked"]:
        check(value in renderer_text, f"renderer provenance control is missing {value!r}")

    publisher_text = json.dumps(publisher, sort_keys=True)
    for gate in EXPECTED_GATES:
        check(gate in publisher_text, f"publisher does not verify approval {gate}")
    for value in [
        "thumbnails/set",
        "containsSyntheticMedia",
        "publishAt",
        "scheduled publication requires private upload status",
        "__YOUTUBE_CHANNEL_ID__",
    ]:
        check(value in publisher_text, f"publisher is missing {value!r}")
    check(
        targets(publisher, "Validate Release Package") == ["Verify Publisher OAuth Channel"]
        and targets(publisher, "Enforce Publisher Channel Identity") == ["Download Final Render"],
        "publisher must verify the configured channel before downloading or uploading media",
    )
    upload = node_by_name(publisher, "Upload Private or Approved Release")
    check(upload["parameters"].get("binaryProperty") == "video", "publisher upload must consume video binary")
    check("publishAt" in upload["parameters"].get("options", {}), "publisher upload does not forward publishAt")
    thumbnail = node_by_name(publisher, "Set YouTube Thumbnail")
    check(thumbnail["parameters"].get("contentType") == "binaryData", "thumbnail upload must use binary body")

    schedule = node_by_name(analytics, "Daily 08:15 ET")
    interval = schedule["parameters"].get("rule", {}).get("interval", [{}])[0]
    check((interval.get("triggerAtHour"), interval.get("triggerAtMinute")) == (8, 15), "analytics schedule must be 08:15")
    check(analytics.get("settings", {}).get("timezone") == "America/New_York", "analytics timezone must be America/New_York")
    check(
        targets(analytics, "Daily 08:15 ET") == ["Verify Analytics OAuth Channel"]
        and targets(analytics, "Manual Analytics Run") == ["Verify Analytics OAuth Channel"],
        "analytics must verify the configured channel before querying metrics",
    )
    check("__YOUTUBE_CHANNEL_ID__" in json.dumps(analytics), "analytics channel identity pin is missing")
    check(node_by_name(analytics, "Upsert Analytics Snapshots").get("alwaysOutputData") is True, "analytics upsert must emit on zero inserted rows")
    check(node_by_name(analytics, "Build 14-Day Comparison").get("alwaysOutputData") is True, "analytics comparison must emit on zero rows")

    state_text = json.dumps(state, sort_keys=True)
    for table in ["rahasya_projects", "rahasya_events", "rahasya_rights_provenance", "rahasya_cost_ledger"]:
        check(table in state_text, f"state workflow does not persist {table}")
    check("rahasya_approvals" in approval_text, "approval workflow does not persist rahasya_approvals")

    suite_text = json.dumps(list(workflows.values()), sort_keys=True)
    check("x-omniroute-fallback\"" not in suite_text, "deprecated OmniRoute fallback telemetry header is present")
    check("x-omniroute-fallback-attempts" in suite_text, "fallback-attempt telemetry is not captured")
    for safety_phrase in ["untrusted evidence", "Do not invent", "strict JSON", "US-based"]:
        check(safety_phrase.lower() in suite_text.lower(), f"agent safety/market policy is missing {safety_phrase!r}")


def validate_migration() -> None:
    try:
        sql = MIGRATION_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"cannot read migration: {exc}") from exc
    normalized = sql.upper()
    check("BEGIN;" in normalized and "COMMIT;" in normalized, "migration must be transactional")
    check("DROP TABLE" not in normalized and "TRUNCATE" not in normalized, "migration contains a destructive table operation")
    tables = [
        "rahasya_projects",
        "rahasya_events",
        "rahasya_approvals",
        "rahasya_rights_provenance",
        "rahasya_cost_ledger",
        "rahasya_analytics_snapshots",
        "rahasya_growth_recommendations",
    ]
    for table in tables:
        check(re.search(rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{table}\b", sql, re.I) is not None, f"migration does not create {table}")
    for pattern in SECRET_PATTERNS:
        check(pattern.search(sql) is None, f"migration matches secret pattern {pattern.pattern!r}")


def main() -> int:
    try:
        manifest = load_json(MANIFEST_PATH)
        check(manifest.get("suite") == "rahasya-global", "manifest suite is invalid")
        check(manifest.get("schema_version") == 1, "manifest schema version is invalid")
        entries = manifest.get("workflows")
        check(isinstance(entries, list), "manifest workflows must be a list")
        files = [entry.get("file") for entry in entries]
        check(files == EXPECTED_FILES, "manifest files or import order changed")
        names = [entry.get("name") for entry in entries]
        check(len(names) == len(set(names)) == 19, "manifest must have 19 unique workflow names")
        activatable = [entry["file"] for entry in entries if entry.get("activatable")]
        check(activatable == EXPECTED_FILES[-2:], "only master and analytics may be activatable")

        workflows: dict[str, dict[str, Any]] = {}
        global_node_ids: set[str] = set()
        all_serialized = ""
        for entry in entries:
            path = ROOT / entry["file"]
            check(path.is_file(), f"missing workflow file {entry['file']}")
            workflow = load_json(path)
            check(workflow.get("name") == entry["name"], f"manifest name mismatch for {entry['file']}")
            check(workflow.get("active") is False, f"generated workflow must be inactive: {entry['name']}")
            check(workflow.get("settings", {}).get("executionOrder") == "v1", f"{entry['name']}: executionOrder must be v1")
            validate_graph(workflow, global_node_ids)
            validate_credentials(workflow)
            validate_http_nodes(workflow)
            workflows[entry["file"]] = workflow
            serialized = json.dumps(workflow, sort_keys=True)
            all_serialized += serialized
            check("$env" not in serialized, f"{entry['name']}: runtime environment access bypasses installer validation")
            for pattern in SECRET_PATTERNS:
                check(pattern.search(serialized) is None, f"{entry['name']}: possible committed secret ({pattern.pattern})")

        validate_suite(workflows)
        placeholders = set(re.findall(r"__[A-Z0-9_]+__", all_serialized))
        check(placeholders <= ALLOWED_PLACEHOLDERS, f"unknown placeholders: {sorted(placeholders - ALLOWED_PLACEHOLDERS)}")
        check(ALLOWED_PLACEHOLDERS <= placeholders, f"expected placeholders are unused: {sorted(ALLOWED_PLACEHOLDERS - placeholders)}")
        validate_migration()
    except ValidationError as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    print("Validated 19 workflows: manifest, graphs, credentials, runtime readiness, HTTP schemas, safety controls, release gates, telemetry, and migration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
