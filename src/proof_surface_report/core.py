"""Render proof-surface JSON artifacts as a concise Markdown handoff report.

This adapter is self-contained and stdlib-only. It consumes the neutral
proof-surface packet shape plus EMET witness receipts and emits reviewer-facing
Markdown. It does not certify, trust, approve, sign, upload, or enforce
anything.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

STATUS_ORDER = {"blocked": 3, "needs-polish": 2, "unknown": 1, "ready": 0}
PACKET_STATUSES = {"ready", "needs-polish", "blocked", "unknown"}
CHECK_STATUSES = {"pass", "warn", "fail", "unknown"}
RECEIPT_VERDICTS = {
    "MATCH",
    "DRIFT",
    "UNVERIFIABLE",
    "COHERENT",
    "VIEW_DIFFERS_FROM_SOURCE",
    "CORROBORATED",
    "QUARANTINE_READ_PATH_DIVERGENCE",
}
ROOT_FIELDS = {
    "proof_surface_version",
    "packet_id",
    "surface",
    "status",
    "claims",
    "checks",
    "action_items",
}
CLAIM_FIELDS = {"claim", "evidence"}
CHECK_FIELDS = {"tool", "status", "summary"}
RECEIPT_FIELDS = {
    "receipt_id",
    "verdict",
    "witness",
    "subject",
    "evidence",
    "notes",
}
WITNESS_FIELDS = {"implementation", "spec_version", "self_sha256", "check"}
SUBJECT_FIELDS = {"name", "digest"}
DIGEST_FIELDS = {"sha256"}
EVIDENCE_FIELDS = {"exit_code", "stdout_verdict_line"}
AUTHORITY_PATTERNS = (
    (
        "authority-token",
        re.compile(
            r"(?<![A-Z0-9_])"
            r"(?:TRUSTED|APPROVED|SAFE|ALLOWED|PERMITTED|AUTHORIZED|CERTIFIED|COMPLIANT)"
            r"(?![A-Z0-9_])"
        ),
    ),
    ("trusted", re.compile(r"\btrust(?:ed|worthy)?\b", re.IGNORECASE)),
    ("approved", re.compile(r"\bapprov(?:e|es|ed|al)\b", re.IGNORECASE)),
    ("authorized", re.compile(r"\bauthori[sz](?:e|es|ed|ation)\b", re.IGNORECASE)),
    ("certified", re.compile(r"\bcertif(?:y|ies|ied|ication)\b", re.IGNORECASE)),
    ("compliant", re.compile(r"\bcomplian(?:t|ce)\b", re.IGNORECASE)),
    ("safe-for-release", re.compile(r"\bsafe\s+(?:to|for)\b", re.IGNORECASE)),
    ("permitted", re.compile(r"\bpermit(?:s|ted)?\b", re.IGNORECASE)),
    ("allowed", re.compile(r"\ballow(?:s|ed)?\b", re.IGNORECASE)),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render proof-surface packet or witness receipt JSON as Markdown."
    )
    parser.add_argument("artifacts", nargs="+", type=Path, help="JSON artifacts.")
    parser.add_argument(
        "--title",
        default="Proof Surface Handoff Report",
        help="Markdown report title.",
    )
    return parser


def load_artifact(path: Path) -> tuple[str, dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    if data.get("proof_surface_version") == "0.1":
        validate_packet(path, data)
        return "packet", data
    if "receipt_id" in data and "verdict" in data:
        validate_receipt(path, data)
        return "witness_receipt", data
    raise ValueError(f"{path} is not a proof-surface packet or witness receipt")


def validate_packet(path: Path, data: dict[str, Any]) -> None:
    issues: list[str] = []
    reject_unknown(data, "$", ROOT_FIELDS, issues)
    require_text(data, "packet_id", issues)
    require_text(data, "surface", issues)
    require_enum(data, "status", PACKET_STATUSES, issues)
    reject_authority_language(data.get("surface"), "$.surface", issues)
    validate_claims(data.get("claims"), issues)
    validate_checks(data.get("checks"), issues)
    validate_actions(data.get("action_items"), issues)
    if issues:
        raise ValueError(f"{path} packet validation failed: " + "; ".join(issues))


def validate_receipt(path: Path, data: dict[str, Any]) -> None:
    issues: list[str] = []
    reject_unknown(data, "$", RECEIPT_FIELDS, issues)
    require_text(data, "receipt_id", issues)
    require_enum(data, "verdict", RECEIPT_VERDICTS, issues)
    validate_witness(data.get("witness"), issues)
    validate_subjects(data.get("subject"), issues)
    validate_receipt_evidence(data.get("evidence"), issues)
    reject_authority_language(data.get("notes"), "$.notes", issues)
    if issues:
        raise ValueError(f"{path} receipt validation failed: " + "; ".join(issues))


def reject_unknown(data: dict[str, Any], path: str, allowed: set[str], issues: list[str]) -> None:
    for field in sorted(set(data) - allowed):
        issues.append(f"{path}.{field} unexpected field")


def require_text(
    data: dict[str, Any],
    field: str,
    issues: list[str],
    path: str | None = None,
) -> None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{path or f'$.{field}'} expected non-empty string")


def require_object(
    value: Any,
    path: str,
    allowed: set[str],
    issues: list[str],
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        issues.append(f"{path} expected object")
        return None
    reject_unknown(value, path, allowed, issues)
    return value


def require_enum(
    data: dict[str, Any],
    field: str,
    allowed: set[str],
    issues: list[str],
    path: str | None = None,
) -> None:
    if data.get(field) not in allowed:
        issues.append(f"{path or f'$.{field}'} expected one of: {', '.join(sorted(allowed))}")


def reject_authority_language(value: Any, path: str, issues: list[str]) -> None:
    if not isinstance(value, str):
        return
    for label, pattern in AUTHORITY_PATTERNS:
        if pattern.search(value):
            issues.append(f"{path} contains authority-shaped wording: {label}")


def validate_claims(value: Any, issues: list[str]) -> None:
    if not isinstance(value, list):
        issues.append("$.claims expected array")
        return
    if not value:
        issues.append("$.claims expected at least one item")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            issues.append(f"$.claims[{index}] expected object")
            continue
        reject_unknown(item, f"$.claims[{index}]", CLAIM_FIELDS, issues)
        require_text(item, "claim", issues, f"$.claims[{index}].claim")
        require_text(item, "evidence", issues, f"$.claims[{index}].evidence")
        reject_authority_language(item.get("claim"), f"$.claims[{index}].claim", issues)
        reject_authority_language(item.get("evidence"), f"$.claims[{index}].evidence", issues)


def validate_checks(value: Any, issues: list[str]) -> None:
    if not isinstance(value, list):
        issues.append("$.checks expected array")
        return
    if not value:
        issues.append("$.checks expected at least one item")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            issues.append(f"$.checks[{index}] expected object")
            continue
        reject_unknown(item, f"$.checks[{index}]", CHECK_FIELDS, issues)
        require_text(item, "tool", issues, f"$.checks[{index}].tool")
        require_enum(item, "status", CHECK_STATUSES, issues, f"$.checks[{index}].status")
        require_text(item, "summary", issues, f"$.checks[{index}].summary")
        reject_authority_language(item.get("summary"), f"$.checks[{index}].summary", issues)


def validate_actions(value: Any, issues: list[str]) -> None:
    if not isinstance(value, list):
        issues.append("$.action_items expected array")
        return
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            issues.append(f"$.action_items[{index}] expected non-empty string")
            continue
        reject_authority_language(item, f"$.action_items[{index}]", issues)


def validate_witness(value: Any, issues: list[str]) -> None:
    witness = require_object(value, "$.witness", WITNESS_FIELDS, issues)
    if witness is None:
        return
    require_text(witness, "implementation", issues, "$.witness.implementation")
    require_text(witness, "spec_version", issues, "$.witness.spec_version")
    require_text(witness, "self_sha256", issues, "$.witness.self_sha256")
    require_text(witness, "check", issues, "$.witness.check")
    reject_authority_language(witness.get("implementation"), "$.witness.implementation", issues)
    reject_authority_language(witness.get("check"), "$.witness.check", issues)


def validate_subjects(value: Any, issues: list[str]) -> None:
    if not isinstance(value, list):
        issues.append("$.subject expected array")
        return
    for index, item in enumerate(value):
        subject = require_object(item, f"$.subject[{index}]", SUBJECT_FIELDS, issues)
        if subject is None:
            continue
        require_text(subject, "name", issues, f"$.subject[{index}].name")
        reject_authority_language(subject.get("name"), f"$.subject[{index}].name", issues)
        digest = require_object(
            subject.get("digest"),
            f"$.subject[{index}].digest",
            DIGEST_FIELDS,
            issues,
        )
        if digest is not None:
            require_text(digest, "sha256", issues, f"$.subject[{index}].digest.sha256")


def validate_receipt_evidence(value: Any, issues: list[str]) -> None:
    evidence = require_object(value, "$.evidence", EVIDENCE_FIELDS, issues)
    if evidence is None:
        return
    if not isinstance(evidence.get("exit_code"), int):
        issues.append("$.evidence.exit_code expected integer")
    line = evidence.get("stdout_verdict_line")
    if not isinstance(line, str):
        issues.append("$.evidence.stdout_verdict_line expected string")
    reject_authority_language(line, "$.evidence.stdout_verdict_line", issues)


def text(value: Any, default: str = "unknown") -> str:
    return value if isinstance(value, str) and value else default


def array(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def aggregate_status(packets: list[dict[str, Any]]) -> str:
    if not packets:
        return "unknown"
    return max(
        (text(packet.get("status")) for packet in packets),
        key=lambda status: STATUS_ORDER.get(status, STATUS_ORDER["unknown"]),
    )


def count_items(packets: list[dict[str, Any]], field: str) -> int:
    return sum(len(array(packet.get(field))) for packet in packets)


def render_summary(
    lines: list[str],
    packets: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
) -> None:
    lines.extend(
        [
            "## Summary",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Packets | {len(packets)} |",
            f"| Witness receipts | {len(receipts)} |",
            f"| Aggregate status | {aggregate_status(packets)} |",
            f"| Claims | {count_items(packets, 'claims')} |",
            f"| Checks | {count_items(packets, 'checks')} |",
            f"| Action items | {count_items(packets, 'action_items')} |",
            "",
        ]
    )


def render_packet(lines: list[str], path: Path, packet: dict[str, Any]) -> None:
    lines.extend(
        [
            f"## {text(packet.get('surface'))}",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Packet | {text(packet.get('packet_id'))} |",
            f"| Status | {text(packet.get('status'))} |",
            f"| Source | `{path.as_posix()}` |",
            "",
            "### Claims",
            "",
        ]
    )
    claims = array(packet.get("claims"))
    lines.extend(render_claim(claim) for claim in claims) if claims else lines.append("- none")
    lines.extend(["", "### Checks", ""])
    checks = array(packet.get("checks"))
    lines.extend(render_check(check) for check in checks) if checks else lines.append("- none")
    lines.extend(["", "### Action Items", ""])
    actions = array(packet.get("action_items"))
    lines.extend(f"- {text(action)}" for action in actions) if actions else lines.append("- none")
    lines.append("")


def render_receipt(lines: list[str], path: Path, receipt: dict[str, Any]) -> None:
    witness = receipt.get("witness") if isinstance(receipt.get("witness"), dict) else {}
    evidence = receipt.get("evidence") if isinstance(receipt.get("evidence"), dict) else {}
    lines.extend(
        [
            f"## Witness Receipt: {text(receipt.get('receipt_id'))}",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Verdict | {text(receipt.get('verdict'))} |",
            f"| Witness | {text(witness.get('implementation'))} |",
            f"| Check | {text(witness.get('check'))} |",
            f"| Source | `{path.as_posix()}` |",
            f"| Exit code | {text(str(evidence.get('exit_code', 'unknown')))} |",
            "",
            "### Subject",
            "",
        ]
    )
    subjects = array(receipt.get("subject"))
    lines.extend(render_subject(item) for item in subjects) if subjects else lines.append("- none")
    lines.extend(["", "### Evidence", ""])
    lines.append(f"- stdout verdict line: {text(evidence.get('stdout_verdict_line'))}")
    lines.append(f"- notes: {text(receipt.get('notes'))}")
    lines.append("")


def render_claim(claim: Any) -> str:
    if not isinstance(claim, dict):
        return f"- {text(claim)}"
    return f"- {text(claim.get('claim'))} Evidence: {text(claim.get('evidence'))}"


def render_check(check: Any) -> str:
    if not isinstance(check, dict):
        return f"- {text(check)}"
    return (
        f"- {text(check.get('tool'))}: {text(check.get('status'))}. "
        f"{text(check.get('summary'))}"
    )


def render_subject(subject: Any) -> str:
    if not isinstance(subject, dict):
        return f"- {text(subject)}"
    digest = subject.get("digest") if isinstance(subject.get("digest"), dict) else {}
    return f"- {text(subject.get('name'))}: sha256={text(digest.get('sha256'))}"


def render_report(title: str, artifact_paths: list[Path]) -> str:
    title_issues: list[str] = []
    reject_authority_language(title, "$.title", title_issues)
    if title_issues:
        raise ValueError("report title validation failed: " + "; ".join(title_issues))

    artifacts = [(path, *load_artifact(path)) for path in artifact_paths]
    packets = [data for _, kind, data in artifacts if kind == "packet"]
    receipts = [data for _, kind, data in artifacts if kind == "witness_receipt"]
    lines = [
        f"# {title}",
        "",
        "This report summarizes proof-surface artifacts. It is an evidence handoff,",
        "not a certification, safety verdict, or authority claim.",
        "",
    ]
    render_summary(lines, packets, receipts)
    for path, kind, data in artifacts:
        if kind == "packet":
            render_packet(lines, path, data)
        else:
            render_receipt(lines, path, data)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        print(render_report(args.title, args.artifacts))
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
