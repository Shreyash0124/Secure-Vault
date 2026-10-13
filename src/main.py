from prerequisites import check_prerequisites
from configuration import collect_s3_configuration
from terraform_generator import generate_terraform
from terraform_manager import check_terraform_configuration
from infrastructure_viewer import view_infrastructure
from terminal_ui import main as launch_terminal_ui

def create_s3_configuration():
    """Collect, generate, initialize, and validate an S3 configuration."""

    try:
        configuration = collect_s3_configuration()

        generated_file = generate_terraform(configuration)
        generated_dir = generated_file.parent

        print("\n[INFO] Initializing and validating Terraform...")

        if not check_terraform_configuration(generated_dir):
            print("\n[ERROR] Configuration validation failed.")
            print("[INFO] Review the Terraform errors before proceeding.")
            return

        print("\n" + "=" * 44)
        print("       CONFIGURATION READY FOR REVIEW")
        print("=" * 44)
        print("[SUCCESS] Terraform configuration generated.")
        print("[SUCCESS] Terraform validation passed.")
        print("[INFO] No AWS resources have been created.")

    except (ValueError, OSError, KeyError) as error:
        print(f"\n[ERROR] Could not complete configuration: {error}")


def display_menu():
    print("\n" + "=" * 44)
    print("           SECUREVAULT CLOUD")
    print("=" * 44)
    print("1. Check Prerequisites")
    print("2. Generate and Validate S3 Configuration")
    print("3. Validate Existing Terraform Configuration")
    print("4. View Infrastructure")
    print("5. Destroy Infrastructure")
    print("6. Exit")
    print("=" * 44)


def legacy_text_menu():
    """Fallback text menu retained from the original main.py."""
    while True:
        display_menu()
        choice = input("Select an option: ").strip()

        if choice == "1":
            check_prerequisites()

        elif choice == "2":
            create_s3_configuration()

        elif choice == "3":
            check_terraform_configuration()

        elif choice == "4":
            view_infrastructure()

        elif choice == "5":
            print("\n[INFO] Infrastructure destruction is not implemented yet.")

        elif choice == "6":
            print("\nExiting SecureVault. Goodbye!")
            break

        else:
            print("\n[ERROR] Invalid option. Please select 1-6.")


def main():
    """Launch the polished terminal UI implemented in terminal_ui.py."""
    launch_terminal_ui()


if __name__ == "__main__":
    main()
