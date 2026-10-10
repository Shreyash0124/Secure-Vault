
# SecureVault Cloud

SecureVault Cloud is a beginner-friendly CLI project designed to
generate and validate Terraform configurations for secure AWS S3
infrastructure.

## Current Features

- Python and Terraform prerequisite checks
- Interactive S3 bucket configuration
- S3 bucket name validation
- Terraform configuration generation
- S3 public access blocking
- AES256 server-side encryption
- Optional S3 bucket versioning
- Terraform initialization and validation
- Protection against overwriting existing Terraform files
- Automated unit tests

## Technology Stack

- Python 3.11+
- Terraform
- AWS CLI
- Amazon S3
- HashiCorp AWS Terraform provider

## Project Structure

```text
Plan-2-Local-CLI/
|-- src/
|   |-- main.py
|   |-- prerequisites.py
|   |-- configuration.py
|   |-- terraform_generator.py
|   `-- terraform_manager.py
|-- terraform/
|   |-- main.tf
|   `-- .terraform.lock.hcl
|-- tests/
|   |-- test_configuration.py
|   |-- test_terraform_generator.py
|   `-- test_terraform_manager.py
|-- README.md
|-- requirements.txt
`-- .gitignore
```

## Requirements

* Python 3.10 or newer
* Terraform installed and available through PATH
* Internet access when downloading Terraform providers
* AWS credentials and appropriate permissions for future live
  infrastructure operations

Live AWS operations are not currently implemented.

## Run SecureVault

Open PowerShell in the project root:

```powershell
python src/main.py
```

## Run Tests

```powershell
python -m unittest discover -s tests -v
```

The tests validate application logic without creating AWS resources.

## Security Notes

The generated S3 configuration enables:

* Blocking public ACLs
* Blocking public bucket policies
* Ignoring public ACLs
* Restricting public bucket access
* AES256 server-side encryption
* Optional object versioning

These settings are useful security controls, but they do not
guarantee complete security.

Versioning is not a substitute for backups, and encryption at
rest does not replace access control or credential protection.

## Current Limitations

* Live infrastructure deployment is not implemented.
* Infrastructure inspection is not implemented.
* Infrastructure destruction is not implemented.
* AWS permissions and live security settings have not been tested.

## Development Status

Local development and automated testing are in progress.
No AWS resources have been created by this project.
