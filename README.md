SecureVault Cloud

Secure infrastructure. Simplified.

A beginner-friendly, local-first CLI for generating and reviewing
Terraform configurations for AWS S3 security.






Contents

Overview

Features

How it works

Requirements

Getting started

Run the tests

Project structure

Safety and limitations

Overview

SecureVault Cloud is an experimental Python command-line project
that helps users generate and inspect Terraform configuration for AWS S3
buckets with foundational security controls.

The goal is to make common infrastructure-security settings easier to
understand and configure without requiring users to write every
Terraform resource by hand.

Current scope: SecureVault works locally. It can generate
Terraform configuration and run Terraform initialization and
validation. It does not deploy infrastructure or verify the live
state of an AWS account.

Features

Interactive CLI for configuring an S3 bucket.

Input validation for bucket names and configuration choices.

Terraform generation for S3 infrastructure.

Public-access protections enabled by default in generated
configurations.

Optional versioning for the bucket.

Encryption options supported by the configuration workflow.

Local security audit for selected Terraform configuration files.

Configuration inventory and registry for local configuration
metadata and the latest recorded audit.

Overwrite protection to reduce accidental replacement of generated
configurations.

Automated tests for configuration, generation, auditing, registry,
and Terraform command restrictions.

The security audit analyzes local Terraform configuration. It is not a
full Terraform language parser, and it does not confirm live AWS
settings, account permissions, or deployed resource state. Review its
findings and the generated Terraform before using them in a real
environment.

How it works

Choose configuration options in the SecureVault CLI.

SecureVault validates the inputs.

The generator writes Terraform configuration files locally.

The security auditor can review local Terraform configuration and
report findings.

Terraform initialization and validation can be run to check the
configuration.

These steps do not create AWS infrastructure.

Requirements

Windows with PowerShell or Command Prompt

Python 3.11 or later

Terraform CLI installed and available on PATH

AWS credentials are not needed for local configuration generation and
static auditing. Terraform provider initialization may require network
access to download the provider.

Getting started (Windows)

Download or clone this repository.

Open a terminal in the project folder.

Install the Python dependencies:

python -m pip install -r requirements.txt

Confirm Python and Terraform are available:

python --version
terraform version

Launch SecureVault:

.\run_securevault.bat

Run the tests

From the project root:

python -m unittest discover -s tests -v

Project structure

Secure-Vault/
├── src/
│   ├── main.py
│   ├── terminal_ui.py
│   ├── prerequisites.py
│   ├── configuration.py
│   ├── configuration_registry.py
│   ├── infrastructure_viewer.py
│   ├── security_auditor.py
│   ├── terraform_generator.py
│   └── terraform_manager.py
├── terraform/
│   ├── main.tf
│   └── .terraform.lock.hcl
├── tests/
├── requirements.txt
├── run_securevault.bat
├── README.md
└── .gitignore

Terraform provider downloads, Python caches, local generated
configurations, and state files should not be committed.

Safety and limitations

The current CLI does not enable terraform apply or
terraform destroy.

SecureVault does not create or modify AWS resources.

Static audit results describe local files only; live AWS configuration
is not verified.

A customer-managed KMS key ARN does not prove the key exists or that
permissions are correct.

Keep credentials, .env files, Terraform state, private keys, and
other sensitive data out of version control.

Review generated Terraform and understand its effects before using it
outside a local demonstration.

Development status

SecureVault Cloud is a work in progress intended for learning and
demonstration. Features and interfaces may change. Contributions, bug
reports, and suggestions are welcome.

SecureVault Cloud — Build securely. Configure confidently.