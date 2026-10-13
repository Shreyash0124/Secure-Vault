"""Static security checks for SecureVault Cloud Terraform configuration.

This module audits local Terraform text only. It does not contact AWS and cannot
verify the deployed state of any resource.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def extract_resource_blocks(text: str) -> list[dict[str, str]]:
    """Extract Terraform resource blocks using brace counting while respecting strings."""
    resources: list[dict[str, str]] = []
    header = re.compile(r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{')
    pos = 0

    while True:
        match = header.search(text, pos)
        if not match:
            break
        start = match.end()
        depth = 1
        in_string = False
        escaped = False
        i = start

        while i < len(text) and depth:
            char = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            else:
                if char == '"':
                    in_string = True
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
            i += 1

        body = text[start:i - 1] if depth == 0 else text[start:]
        resources.append({
            "type": match.group(1),
            "name": match.group(2),
            "body": body,
        })
        pos = i if i > match.end() else match.end()

    return resources


def assignments(text: str) -> dict[str, str]:
    """Return simple literal or reference assignments; complex expressions stay unknown."""
    result: dict[str, str] = {}
    pattern = re.compile(r'(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*("[^"\n]*"|[A-Za-z_][A-Za-z0-9_.\[\]-]*|true|false|null)\s*(?:#.*)?$')
    for match in pattern.finditer(text):
        result[match.group(1)] = match.group(2).strip('"')
    return result


def _recommendation(rule: str, status: str, verdict: str, details: str) -> str:
    """Return practical guidance tailored to the specific audit result."""
    verdict_key = next(
        (key for key in ("FAIL", "WARN", "UNKNOWN", "PASS") if verdict.upper().startswith(key)),
        "UNKNOWN",
    )
    status_lower = status.lower()
    details_lower = details.lower()

    if rule == "S3 Bucket Resource":
        if status == "Not found":
            return "Add one aws_s3_bucket resource, then reference it from the related security resources."
        if status == "Ambiguous":
            return "Audit one intended bucket at a time, or explicitly identify and validate each bucket separately."
    if rule == "Server-Side Encryption":
        if status == "Not found":
            return "Add an S3 server-side encryption configuration using AES256 or aws:kms."
        if "unsupported" in status_lower or "conflicting" in status_lower:
            return "Use one supported encryption algorithm: AES256 or aws:kms; remove conflicting KMS settings."
        if "association" in status_lower or verdict_key == "UNKNOWN":
            return "Confirm the encryption resource references the intended aws_s3_bucket resource and uses static, unambiguous settings."
        if "kms" in status_lower:
            return "Confirm the chosen KMS key exists and the required AWS principals have permission to use it."
        if verdict_key == "PASS":
            return "Keep server-side encryption enabled; this local audit does not verify the live AWS setting."
    if rule == "S3 Access Protection":
        if status == "Not found":
            return "Add aws_s3_bucket_public_access_block with all four protection settings set to true."
        if "disabled" in status_lower:
            return "Set every public-access protection listed in the finding to true."
        if status == "Incomplete":
            return "Explicitly set all four public-access protection attributes to true."
        if status == "Ambiguous" or "association" in status_lower:
            return "Ensure exactly one applicable public-access block is present and references the intended bucket."
        if verdict_key == "PASS":
            return "Keep all four public-access protections true; verify live AWS settings separately when authorized."
    if rule == "Bucket Versioning":
        if status == "Not found":
            return "Enable versioning if recovery from accidental overwrites or deletions is required; otherwise confirm the choice is intentional."
        if status == "Suspended":
            return "Set versioning status to Enabled if you need protection from accidental overwrites or deletions."
        if status == "Ambiguous" or "association" in status_lower:
            return "Ensure one versioning resource references the intended bucket and has a clear status."
        if verdict_key == "PASS":
            return "Keep versioning enabled if recovery from accidental overwrites or deletions is required."
    if verdict_key == "UNKNOWN":
        return "Resolve the uncertainty described in the finding before treating this check as verified."
    if verdict_key == "FAIL":
        return "Correct the configuration issue described in the finding, then rerun the local audit."
    if verdict_key == "WARN":
        return "Review whether this setting matches the bucket's intended security and recovery requirements."
    return "Keep this setting in place and verify the live AWS configuration separately when authorized."


def _finding(rule: str, status: str, severity: str, verdict: str, details: str) -> dict[str, str]:
    return {
        "security_rule": rule,
        "rule": rule,
        "status": status,
        "severity": severity,
        "verdict": verdict,
        "details": details,
        "recommendation": _recommendation(rule, status, verdict, details),
    }


def _bucket_reference(body: str) -> str | None:
    values = assignments(body)
    value = values.get("bucket")
    if value and value.startswith("aws_s3_bucket."):
        match = re.match(r"aws_s3_bucket\.([A-Za-z0-9_-]+)(?:\.(?:id|arn|bucket))?$", value)
        return match.group(1) if match else None
    return None


def audit_terraform(terraform_path: str | Path) -> dict[str, Any]:
    """Audit local .tf files for common S3 security configuration issues."""
    path = Path(terraform_path)
    if path.is_dir():
        files = sorted(path.glob("*.tf"))
        text = "\n".join(file.read_text(encoding="utf-8") for file in files)
    else:
        text = path.read_text(encoding="utf-8")

    resources = extract_resource_blocks(text)
    buckets = [r for r in resources if r["type"] == "aws_s3_bucket"]
    bucket_name = "Unknown"
    expected_bucket: str | None = None

    if len(buckets) == 1:
        expected_bucket = buckets[0]["name"]
        bucket_value = assignments(buckets[0]["body"]).get("bucket")
        if bucket_value and not bucket_value.startswith("var.") and not bucket_value.startswith("local."):
            bucket_name = bucket_value

    findings: list[dict[str, str]] = []

    if not buckets:
        findings.append(_finding(
            "S3 Bucket Resource", "Not found", "HIGH", "FAIL",
            "No aws_s3_bucket resource was found; dependent S3 security settings cannot be tied to a bucket.",
        ))
    elif len(buckets) > 1:
        findings.append(_finding(
            "S3 Bucket Resource", "Ambiguous", "HIGH", "UNKNOWN",
            "Multiple aws_s3_bucket resources were found; this audit cannot determine which bucket is the target.",
        ))

    def association_issue(resource: dict[str, str]) -> bool:
        # For a unique bucket, require an explicit reference to that exact resource.
        # Literal/absent associations and references to another bucket are not treated as verified.
        if len(buckets) != 1:
            return True
        ref = _bucket_reference(resource["body"])
        return ref != expected_bucket

    # Encryption
    encryptions = [r for r in resources if r["type"] == "aws_s3_bucket_server_side_encryption_configuration"]
    if not encryptions:
        findings.append(_finding(
            "Server-Side Encryption", "Not found", "HIGH", "FAIL",
            "No S3 server-side encryption configuration resource was found.",
        ))
    elif len(encryptions) > 1:
        findings.append(_finding(
            "Server-Side Encryption", "Ambiguous", "HIGH", "UNKNOWN",
            "Multiple encryption configuration resources were found; the target configuration is ambiguous.",
        ))
    elif association_issue(encryptions[0]):
        findings.append(_finding(
            "Server-Side Encryption", "Association unknown", "HIGH", "UNKNOWN",
            "The encryption resource cannot be verified as attached to the single intended S3 bucket.",
        ))
    else:
        body = encryptions[0]["body"]
        algorithms = re.findall(r'\bsse_algorithm\s*=\s*"([^"]+)"', body)
        kms_keys = re.findall(r'\bkms_master_key_id\s*=\s*"([^"]+)"', body)
        if not algorithms:
            findings.append(_finding(
                "Server-Side Encryption", "Incomplete", "HIGH", "UNKNOWN",
                "The encryption algorithm is not specified as a static value.",
            ))
        elif len(set(algorithms)) != 1:
            findings.append(_finding(
                "Server-Side Encryption", "Ambiguous", "HIGH", "UNKNOWN",
                "Conflicting encryption algorithms were found.",
            ))
        elif algorithms[0] == "AES256":
            if kms_keys:
                findings.append(_finding(
                    "Server-Side Encryption", "Conflicting settings", "HIGH", "FAIL",
                    "AES256 encryption must not be combined with a KMS key ID in this configuration.",
                ))
            else:
                findings.append(_finding(
                    "Server-Side Encryption", "AES256", "INFO", "PASS",
                    "S3 server-side encryption with SSE-S3 (AES256) is configured.",
                ))
        elif algorithms[0] == "aws:kms":
            if len(kms_keys) > 1:
                findings.append(_finding(
                    "Server-Side Encryption", "Ambiguous KMS key", "HIGH", "UNKNOWN",
                    "Multiple KMS key IDs were found.",
                ))
            elif kms_keys and not kms_keys[0].strip():
                findings.append(_finding(
                    "Server-Side Encryption", "Incomplete KMS key", "HIGH", "UNKNOWN",
                    "The configured KMS key ID is empty.",
                ))
            else:
                details = "SSE-KMS is configured; the existence and permissions of any KMS key are not verified."
                findings.append(_finding(
                    "Server-Side Encryption", "SSE-KMS", "INFO", "PASS", details,
                ))
        else:
            findings.append(_finding(
                "Server-Side Encryption", "Unsupported", "HIGH", "FAIL",
                f"Unsupported static encryption algorithm: {algorithms[0]}.",
            ))

    # Public access protection
    access_blocks = [r for r in resources if r["type"] == "aws_s3_bucket_public_access_block"]
    required_access = (
        "block_public_acls",
        "block_public_policy",
        "ignore_public_acls",
        "restrict_public_buckets",
    )
    if not access_blocks:
        findings.append(_finding(
            "S3 Access Protection", "Not found", "CRITICAL", "FAIL",
            "No S3 public access block resource was found.",
        ))
    elif len(access_blocks) > 1:
        findings.append(_finding(
            "S3 Access Protection", "Ambiguous", "CRITICAL", "UNKNOWN",
            "Multiple public access block resources were found.",
        ))
    else:
        values = assignments(access_blocks[0]["body"])
        false_keys = [key for key in required_access if values.get(key) == "false"]
        missing_keys = [key for key in required_access if key not in values or values[key] not in ("true", "false")]
        if false_keys:
            findings.append(_finding(
                "S3 Access Protection", "Public access setting disabled", "CRITICAL", "FAIL",
                "These required protections are explicitly false: " + ", ".join(false_keys) + ".",
            ))
        elif missing_keys:
            findings.append(_finding(
                "S3 Access Protection", "Incomplete", "CRITICAL", "UNKNOWN",
                "Could not verify these required settings: " + ", ".join(missing_keys) + ".",
            ))
        elif association_issue(access_blocks[0]):
            findings.append(_finding(
                "S3 Access Protection", "Association unknown", "CRITICAL", "UNKNOWN",
                "All four settings are true, but the block cannot be tied to the intended bucket.",
            ))
        else:
            findings.append(_finding(
                "S3 Access Protection", "All settings enabled", "INFO", "PASS",
                "All four S3 public access block settings are explicitly true.",
            ))

    # Versioning
    versioning = [r for r in resources if r["type"] == "aws_s3_bucket_versioning"]
    if not versioning:
        findings.append(_finding(
            "Bucket Versioning", "Not found", "MEDIUM", "WARN",
            "No bucket versioning resource was found. Versioning may be intentionally disabled.",
        ))
    elif len(versioning) > 1:
        findings.append(_finding(
            "Bucket Versioning", "Ambiguous", "MEDIUM", "UNKNOWN",
            "Multiple versioning resources were found.",
        ))
    else:
        statuses = re.findall(r'\bstatus\s*=\s*"([^"]+)"', versioning[0]["body"])
        if len(set(statuses)) != 1:
            findings.append(_finding(
                "Bucket Versioning", "Incomplete", "MEDIUM", "UNKNOWN",
                "A single static versioning status could not be determined.",
            ))
        elif statuses[0] == "Enabled" and association_issue(versioning[0]):
            findings.append(_finding(
                "Bucket Versioning", "Association unknown", "MEDIUM", "UNKNOWN",
                "Versioning is enabled in the file, but cannot be tied to the intended bucket.",
            ))
        elif statuses[0] == "Enabled":
            findings.append(_finding(
                "Bucket Versioning", "Enabled", "INFO", "PASS",
                "Bucket versioning is explicitly enabled.",
            ))
        elif statuses[0] == "Suspended":
            findings.append(_finding(
                "Bucket Versioning", "Suspended", "MEDIUM", "WARN",
                "Bucket versioning is suspended.",
            ))
        else:
            findings.append(_finding(
                "Bucket Versioning", "Unsupported", "MEDIUM", "UNKNOWN",
                f"Unrecognized versioning status: {statuses[0]}.",
            ))

    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    findings.sort(key=lambda finding: severity_order.get(finding["severity"], 99))

    return {
        "bucket_name": bucket_name,
        "findings": findings,
        "deployment_status": "Not verified",
    }
