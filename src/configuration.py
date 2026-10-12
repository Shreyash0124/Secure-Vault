import re

BRAND_RED = "#651827"
TEXT_PRIMARY = "#F3F0EB"
TEXT_MUTED = "#B5A0A6"
WARNING = "#C9A15B"


class ConfigurationCancelled(Exception):
    """Raised when the user cancels S3 configuration setup."""


def validate_bucket_name(name):
    if not 3 <= len(name) <= 63:
        return False, "Bucket names must be 3–63 characters long."
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*[a-z0-9]", name):
        return False, "Use lowercase letters, numbers, hyphens, and periods; start/end with a letter or number."
    if ".." in name:
        return False, "Bucket names cannot contain consecutive periods."
    if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", name):
        return False, "Bucket names cannot be formatted as IP addresses."
    if any(part.startswith(("xn--", "sthree-", "amzn-s3-demo-")) for part in name.split(".")):
        return False, "A bucket-name label uses a reserved prefix."
    if name.endswith(("-s3alias", "--ol-s3", ".mrap", "--x-s3", "--table-s3")):
        return False, "This bucket name uses a reserved suffix."
    return True, "Bucket name format is valid."


def _prompt(console, step, title, description):
    from rich import box
    from rich.console import Group
    from rich.panel import Panel
    from rich.text import Text
    console.clear()
    console.print(Panel(
        Group(Text("SECUREVAULT / CONFIGURATION", style=f"bold {BRAND_RED}"),
              Text(""), Text(title, style=f"bold {TEXT_PRIMARY}"),
              Text(description, style=TEXT_MUTED), Text(""),
              Text(f"STEP {step} OF 4", style=f"bold {TEXT_MUTED}")),
        title="[bold]NEW S3 CONFIGURATION[/]", border_style=BRAND_RED,
        box=box.DOUBLE, padding=(1, 2), expand=False))
    value = console.input(f"[bold {BRAND_RED}]  › [/]").strip()
    if value.lower() in {"back", "cancel", "q", ":q", "esc"}:
        raise ConfigurationCancelled("Configuration setup cancelled by user.")
    return value


def collect_s3_configuration():
    from rich import box
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    console = Console()
    while True:
        bucket_name = _prompt(console, 1, "Bucket name",
            "Choose a globally unique name using lowercase letters, numbers, hyphens, or periods.")
        valid, message = validate_bucket_name(bucket_name)
        if valid:
            break
        console.print(Panel(message, title="[bold yellow]INVALID BUCKET NAME[/]",
                            border_style=WARNING, box=box.ROUNDED))
        console.input("[dim]Press Enter to try again...[/]")

    versioning_input = _prompt(console, 2, "Bucket versioning",
        "Versioning preserves prior object versions after overwrites or accidental deletions. Enter yes or no.").lower()
    while versioning_input not in {"yes", "y", "no", "n"}:
        versioning_input = console.input("[yellow]Enter yes or no: [/]").strip().lower()
    versioning = versioning_input in {"yes", "y"}

    console.clear()
    console.print(Panel(
        Group(Text("Choose how objects are encrypted at rest.", style=TEXT_PRIMARY),
              Text(""),
              Text("[1] SSE-S3 (AES256)", style=f"bold {BRAND_RED}"),
              Text("    S3-managed encryption keys.", style=TEXT_MUTED),
              Text(""),
              Text("[2] SSE-KMS (AWS-managed key)", style=f"bold {BRAND_RED}"),
              Text("    Uses the AWS-managed aws/s3 KMS key; KMS permissions and costs may apply.", style=TEXT_MUTED),
              Text(""),
              Text("[3] SSE-KMS (customer-managed key)", style=f"bold {BRAND_RED}"),
              Text("    Uses a KMS key ARN you provide and manage.", style=TEXT_MUTED),
              Text(""), Text("Type back to cancel.", style=TEXT_MUTED)),
        title="[bold]STEP 3 OF 4 · ENCRYPTION[/]", border_style=BRAND_RED,
        box=box.DOUBLE, padding=(1, 2), expand=False))
    choice = console.input(f"[bold {BRAND_RED}]  › [/]").strip().lower()
    if choice in {"back", "cancel", "q", "esc"}:
        raise ConfigurationCancelled("Configuration setup cancelled by user.")
    while choice not in {"1", "2", "3"}:
        choice = console.input("[yellow]Choose 1, 2, or 3: [/]").strip().lower()
        if choice in {"back", "cancel", "q", "esc"}:
            raise ConfigurationCancelled("Configuration setup cancelled by user.")

    encryption = {"1": "AES256", "2": "aws:kms", "3": "aws:kms-customer"}[choice]
    kms_key_arn = None
    if choice == "3":
        kms_key_arn = _prompt(console, 4, "Customer-managed KMS key ARN",
            "Enter the ARN of an existing KMS key in the same AWS region as the bucket.")
        if not re.fullmatch(r"arn:(aws|aws-us-gov|aws-cn):kms:[a-z0-9-]+:\d{12}:key/[0-9a-fA-F-]{36}", kms_key_arn):
            console.print(Panel("That does not look like a KMS key ARN. Restart with the correct ARN.",
                                border_style=WARNING, box=box.ROUNDED))
            raise ConfigurationCancelled("Invalid KMS key ARN format.")

    labels = {"AES256": "SSE-S3 (AES256)",
              "aws:kms": "SSE-KMS (AWS-managed aws/s3 key)",
              "aws:kms-customer": "SSE-KMS (customer-managed key)"}
    console.clear()
    review = Table(box=box.SIMPLE, show_header=False, padding=(0, 1), expand=False)
    review.add_column("Setting", style=TEXT_MUTED, no_wrap=True)
    review.add_column("Value", style=TEXT_PRIMARY)
    review.add_row("Bucket name", bucket_name)
    review.add_row("Versioning", "Enabled" if versioning else "Disabled")
    review.add_row("Encryption", labels[encryption])
    if kms_key_arn:
        review.add_row("KMS key ARN", kms_key_arn)
    review.add_row("Public access", "Blocked (always enabled)")
    console.print(Panel(
        Group(Text("Review your choices before generating Terraform files.", style=TEXT_MUTED),
              Text(""), review, Text(""),
              Text("Local files only — this does not deploy anything to AWS.", style=BRAND_RED),
              Text(""), Text("Enter yes to generate, or back to cancel.", style=TEXT_MUTED)),
        title="[bold]STEP 4 OF 4 · REVIEW CONFIGURATION[/]",
        border_style=BRAND_RED, box=box.DOUBLE, padding=(1, 2), expand=False))
    answer = console.input(f"[bold {BRAND_RED}]  › [/]").strip().lower()
    if answer not in {"yes", "y"}:
        raise ConfigurationCancelled("Configuration setup cancelled by user.")
    return {"bucket_name": bucket_name, "versioning": versioning,
            "encryption": encryption, "kms_key_arn": kms_key_arn}
