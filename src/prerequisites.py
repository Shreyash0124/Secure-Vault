import shutil
import subprocess
import sys


def check_python():
    """Check the Python version running SecureVault."""

    version = sys.version_info

    if version.major == 3 and version.minor >= 10:
        print(f"[OK] Python {version.major}.{version.minor}.{version.micro}")
        return True

    print("[ERROR] Python 3.10 or newer is required.")
    return False


def check_terraform():
    """Check whether Terraform is installed and accessible."""

    terraform_path = shutil.which("terraform")

    if terraform_path is None:
        print("[ERROR] Terraform is not installed or not in PATH.")
        return False

    try:
        result = subprocess.run(
            [terraform_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode != 0:
            print("[ERROR] Terraform could not run.")
            return False

        version = result.stdout.splitlines()[0]
        print(f"[OK] {version}")
        return True

    except (subprocess.TimeoutExpired, OSError) as error:
        print(f"[ERROR] Terraform check failed: {error}")
        return False


def check_prerequisites():
    """Run all local prerequisite checks."""

    print("\n=== SecureVault Prerequisite Check ===\n")

    python_ok = check_python()
    terraform_ok = check_terraform()

    print("\n=== Summary ===")

    if python_ok and terraform_ok:
        print("[SUCCESS] All current prerequisites are satisfied.")
        return True

    print("[WARNING] Some prerequisites need attention.")
    return False


if __name__ == "__main__":
    check_prerequisites()