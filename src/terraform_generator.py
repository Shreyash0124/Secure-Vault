from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENERATED_DIR = PROJECT_ROOT / "generated"


def _validate_configuration(configuration):
    name = configuration.get("bucket_name")
    if (
        not isinstance(name, str)
        or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", name)
        or ".." in name
    ):
        raise ValueError("A valid S3 bucket name is required.")

    encryption = configuration.get("encryption", "AES256")
    if encryption not in {"AES256", "aws:kms", "aws:kms-customer"}:
        raise ValueError("Unsupported encryption choice.")

    key_arn = configuration.get("kms_key_arn")
    if encryption == "aws:kms-customer":
        if not isinstance(key_arn, str) or not re.fullmatch(
            r"arn:(aws|aws-us-gov|aws-cn):kms:[a-z0-9-]+:\d{12}:key/[0-9a-fA-F-]{36}",
            key_arn,
        ):
            raise ValueError("A valid customer-managed KMS key ARN is required.")
    elif key_arn:
        raise ValueError(
            "kms_key_arn must only be set for customer-managed KMS encryption."
        )

    return name, bool(configuration.get("versioning", False)), encryption, key_arn


def render_terraform(configuration):
    """Render Terraform HCL with explicit references between S3 resources."""
    name, versioning, encryption, key_arn = _validate_configuration(configuration)
    algorithm = "aws:kms" if encryption == "aws:kms-customer" else encryption

    lines = [
        "terraform {",
        "  required_providers {",
        "    aws = {",
        '      source  = "hashicorp/aws"',
        '      version = ">= 5.0"',
        "    }",
        "  }",
        "}",
        "",
        'provider "aws" {',
        "  # Region is supplied through the AWS provider environment/configuration.",
        "}",
        "",
        'resource "aws_s3_bucket" "securevault" {',
        f'  bucket = "{name}"',
        "}",
        "",
        'resource "aws_s3_bucket_server_side_encryption_configuration" "securevault" {',
        "  bucket = aws_s3_bucket.securevault.id",
        "",
        "  rule {",
        "    apply_server_side_encryption_by_default {",
        f'      sse_algorithm = "{algorithm}"',
    ]

    if encryption == "aws:kms-customer":
        lines.append(f'      kms_master_key_id = "{key_arn}"')

    lines += [
        "    }",
        "  }",
        "}",
        "",
        'resource "aws_s3_bucket_public_access_block" "securevault" {',
        "  bucket                  = aws_s3_bucket.securevault.id",
        "  block_public_acls       = true",
        "  ignore_public_acls      = true",
        "  block_public_policy     = true",
        "  restrict_public_buckets = true",
        "}",
        "",
    ]

    # A newly created bucket that has never had versioning enabled should not
    # receive a versioning resource with status = "Suspended".
    if versioning:
        lines += [
            'resource "aws_s3_bucket_versioning" "securevault" {',
            "  bucket = aws_s3_bucket.securevault.id",
            "",
            "  versioning_configuration {",
            '    status = "Enabled"',
            "  }",
            "}",
            "",
        ]

    return "\n".join(lines)


def generate_terraform(configuration):
    """Write generated/<bucket>/main.tf without overwriting existing files."""
    name, _, _, _ = _validate_configuration(configuration)
    target_dir = GENERATED_DIR / name
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "main.tf"

    if target.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing Terraform configuration: {target}"
        )

    target.write_text(render_terraform(configuration), encoding="utf-8")
    return target
