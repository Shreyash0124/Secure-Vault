<div align="center">

🔐 SecureVault Cloud

Secure infrastructure. Simplified.

A local-first CLI that makes AWS S3 security configuration easier to understand.

Generate Terraform · Review security controls · Validate locally

<br>





</div>

⚡ What is SecureVault?

SecureVault Cloud is an experimental Python CLI for generating and inspecting Terraform configurations for AWS S3 buckets with foundational security controls.

The idea is simple: make common cloud-security settings easier to configure, inspect, and learn—without hand-writing every Terraform resource.

🧭 Local-first by design: SecureVault currently generates and reviews files on your machine. It does not deploy AWS infrastructure or verify the live state of an AWS account.

✨ What you can do

Capability

What it does

🧩 Interactive configuration

Configure an S3 bucket through a guided CLI.

🛡️ Public-access protection

Enables S3 public-access protections in generated configurations.

🔒 Encryption options

Select from the encryption options supported by the workflow.

🕰️ Optional versioning

Choose whether bucket versioning should be included.

🧪 Local security audit

Inspect selected Terraform files and report potential findings.

🗂️ Configuration inventory

Keep local metadata and the latest recorded audit for configurations.

🧱 Safer file handling

Input validation and overwrite protection help reduce accidental mistakes.

✅ Terraform validation

Initialize and validate configuration without deploying resources.

🔄 How it works

  Configure
     │
     ▼
  Validate inputs
     │
     ▼
  Generate Terraform
     │
     ▼
  Audit local configuration
     │
     ▼
  Terraform init + validate
     │
     ▼
  Review the result

No terraform apply. No AWS resource creation. The workflow stays local.

🚀 Quick start · Windows

1. Get the project

Clone or download this repository, then open PowerShell in the project directory.

2. Install dependencies

python -m pip install -r requirements.txt

3. Check prerequisites

Run these commands separately:

python --version
terraform version

4. Launch SecureVault

.\run_securevault.bat

🧪 Run the tests

From the project root:

python -m unittest discover -s tests -v

## 🗂️ Project Structure

```text
Secure-Vault/
│
├── src/                         # Application source code
│   ├── main.py                  # Application entry point
│   ├── terminal_ui.py           # Terminal interface
│   ├── prerequisites.py         # Environment checks
│   ├── configuration.py         # Configuration handling
│   ├── configuration_registry.py# Configuration metadata registry
│   ├── infrastructure_viewer.py # Infrastructure inventory
│   ├── security_auditor.py      # Local security analysis
│   ├── terraform_generator.py   # Terraform generation
│   └── terraform_manager.py     # Terraform command management
│
├── terraform/                   # Terraform configuration
│   ├── main.tf
│   └── .terraform.lock.hcl
│
├── tests/                       # Automated tests
├── requirements.txt              # Python dependencies
├── run_securevault.bat           # Windows launcher
├── README.md                     # Project documentation
└── .gitignore                    # Git exclusions
```
🛡️ Safety & limitations

No deployment: The current CLI does not enable terraform apply or terraform destroy.

No AWS changes: SecureVault does not create or modify AWS resources.

Local-only audit: Audit findings describe local Terraform files; live AWS configuration is not verified.

Not a full HCL parser: The static auditor does not understand every possible Terraform language construct. Review its findings rather than treating them as a guarantee.

KMS ARN checks: Entering a customer-managed KMS key ARN does not prove the key exists or that permissions are correct.

Keep secrets private: Never commit AWS credentials, .env files, Terraform state, private keys, or other sensitive data.

AWS credentials are not needed for local generation and static auditing. Terraform initialization may need network access to download the AWS provider.

📌 Development status

SecureVault Cloud is a work in progress built for learning and demonstration. Features and interfaces may change. Bug reports, ideas, and contributions are welcome.

<div align="center">

SecureVault Cloud
Build securely. Configure confidently.

</div>