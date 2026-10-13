"""Run explicitly permitted Terraform initialization and validation commands."""

import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TERRAFORM_DIR = PROJECT_ROOT / "terraform"
COMMAND_TIMEOUT_SECONDS = 120


# Only these exact Terraform argument lists are permitted. In particular,
# apply, destroy, plan, and arbitrary extra arguments remain unavailable.
ALLOWED_COMMANDS = {
    "init": ["init", "-input=false"],
    "validate": ["validate"],
}


def _print_output(output):
    """Print subprocess output safely, including partial timeout output."""
    if output is None:
        return
    if isinstance(output, bytes):
        output = output.decode("utf-8", errors="replace")
    output = output.strip()
    if output:
        print(output)


def run_terraform_command(arguments, working_dir=None):
    """Run only explicitly permitted Terraform validation commands."""
    if not arguments:
        print("[ERROR] No Terraform command was provided.")
        return False

    command_name = arguments[0]
    if command_name not in ALLOWED_COMMANDS:
        print(f"[ERROR] Terraform command '{command_name}' is not permitted.")
        return False

    if arguments != ALLOWED_COMMANDS[command_name]:
        print("[ERROR] Unexpected arguments for the Terraform command.")
        return False

    terraform_path = shutil.which("terraform")
    if terraform_path is None:
        print("[ERROR] Terraform is not installed or not in PATH.")
        return False

    target_dir = (
        Path(working_dir).resolve()
        if working_dir is not None
        else TERRAFORM_DIR.resolve()
    )

    if not target_dir.is_dir():
        print(f"[ERROR] Terraform directory does not exist: {target_dir}")
        return False

    if not (target_dir / "main.tf").is_file():
        print(f"[ERROR] No main.tf found in: {target_dir}")
        return False

    command = [terraform_path, *arguments]
    print(f"\n[INFO] Running: {' '.join(command)}")
    print(f"[INFO] Working directory: {target_dir}")
    print(f"[INFO] Timeout: {COMMAND_TIMEOUT_SECONDS} seconds")

    try:
        result = subprocess.run(
            command,
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
        )

        _print_output(result.stdout)
        _print_output(result.stderr)

        if result.returncode != 0:
            print(
                f"[ERROR] Terraform '{command_name}' failed "
                f"with exit code {result.returncode}."
            )
            return False

        return True

    except subprocess.TimeoutExpired as error:
        # TimeoutExpired may contain partial output. It can be bytes even when
        # text=True, so _print_output handles either representation.
        _print_output(error.stdout)
        _print_output(error.stderr)
        print(
            f"[ERROR] Terraform '{command_name}' timed out after "
            f"{COMMAND_TIMEOUT_SECONDS} seconds."
        )
        print(
            "[INFO] The command was stopped by SecureVault; review the output "
            "above before retrying. No apply or destroy command was run."
        )
        return False

    except OSError as error:
        print(f"[ERROR] Could not execute Terraform: {error}")
        return False


def initialize_terraform(working_dir=None):
    """Initialize providers and the Terraform working directory."""
    return run_terraform_command(["init", "-input=false"], working_dir)


def validate_terraform(working_dir=None):
    """Validate Terraform configuration without deploying infrastructure."""
    return run_terraform_command(["validate"], working_dir)


def check_terraform_configuration(working_dir=None):
    """Initialize and validate a specified Terraform configuration."""
    target_dir = (
        Path(working_dir).resolve()
        if working_dir is not None
        else TERRAFORM_DIR.resolve()
    )

    print("\n=== Terraform Configuration Check ===")

    if not initialize_terraform(target_dir):
        return False

    if not validate_terraform(target_dir):
        return False

    print("\n[SUCCESS] Terraform configuration passed validation.")
    return True
