import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENERATED_DIR = PROJECT_ROOT / "generated"


def extract_setting(content, pattern, default="Unknown"):
    """Extract a setting from a generated Terraform configuration."""

    match = re.search(pattern, content, re.MULTILINE)

    if match:
        return match.group(1)

    return default


def inspect_configuration(terraform_file):
    """Read a Terraform file and summarize its S3 security settings."""

    content = terraform_file.read_text(encoding="utf-8")

    bucket_match = re.search(
        r'resource\s+"aws_s3_bucket"\s+"securevault"\s*\{'
        r'([\s\S]*?)\n\}',
        content,
    )

    bucket_name = "Unknown"

    if bucket_match:
        name_match = re.search(
            r'^\s*bucket\s*=\s*"([^"]+)"',
            bucket_match.group(1),
            re.MULTILINE,
        )

        if name_match:
            bucket_name = name_match.group(1)

    encryption = (
        "AES256"
        if re.search(r'sse_algorithm\s*=\s*"AES256"', content)
        else "Not confirmed"
    )

    required_settings = (
        "block_public_acls",
        "block_public_policy",
        "ignore_public_acls",
        "restrict_public_buckets",
    )

    public_access_blocked = all(
        re.search(rf'\b{setting}\s*=\s*true\b', content)
        for setting in required_settings
    )

    versioning_match = re.search(
        r'resource\s+"aws_s3_bucket_versioning"\s+"securevault"\s*\{'
        r'([\s\S]*?)\n\}',
        content,
    )

    versioning_status = "Unknown"

    if versioning_match:
        status_match = re.search(
            r'\bstatus\s*=\s*"(Enabled|Suspended)"',
            versioning_match.group(1),
        )

        if status_match:
            versioning_status = status_match.group(1)

    return {
        "bucket_name": bucket_name,
        "encryption": encryption,
        "public_access": (
            "Blocked" if public_access_blocked else "Not confirmed"
        ),
        "versioning": versioning_status,
        "deployment_status": "Not verified",
        "file": terraform_file,
    }


def view_infrastructure():
    """Display locally generated infrastructure configurations."""

    print("\n" + "=" * 56)
    print("              SECUREVAULT INVENTORY")
    print("=" * 56)

    if not GENERATED_DIR.is_dir():
        print("\n[INFO] No generated configuration directory exists.")
        print("[INFO] Select option 2 to generate a configuration.")
        return

    terraform_files = sorted(GENERATED_DIR.rglob("main.tf"))

    if not terraform_files:
        print("\n[INFO] No generated Terraform configurations found.")
        return

    for index, terraform_file in enumerate(terraform_files, start=1):
        print(f"\n  CONFIGURATION {index}")
        print("  " + "-" * 48)

        try:
            details = inspect_configuration(terraform_file)

            print(f"  Bucket Name       : {details['bucket_name']}")
            print(f"  Encryption        : {details['encryption']}")
            print(f"  Public Access     : {details['public_access']}")
            print(f"  Versioning        : {details['versioning']}")
            print(
                f"  Deployment Status : "
                f"{details['deployment_status']}"
            )
            print(
                f"  File              : "
                f"{details['file'].relative_to(PROJECT_ROOT)}"
            )

        except (OSError, UnicodeError) as error:
            print(
                f"  [ERROR] Could not read configuration: {error}"
            )

    print("\n" + "=" * 56)
    print(f"  Total configurations: {len(terraform_files)}")
    print("=" * 56)
    print("[INFO] This inventory reads local Terraform files.")
    print("[INFO] It does not query AWS or verify deployed resources.")


if __name__ == "__main__":
    view_infrastructure()