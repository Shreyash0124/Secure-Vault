<div align="center">

# 🟢 SecureVault Cloud

### Secure infrastructure. Simplified.

A beginner-friendly CLI for generating and validating
Terraform configurations for secure AWS infrastructure.

<br>

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Terraform](https://img.shields.io/badge/IaC-Terraform-7B42BC?style=flat-square&logo=terraform&logoColor=white)
![AWS](https://img.shields.io/badge/Cloud-AWS-FF9900?style=flat-square&logo=amazonaws&logoColor=white)
![Status](https://img.shields.io/badge/Status-In%20Development-10B981?style=flat-square)

<br>

**[Features](#-features) · [Architecture](#-how-it-works) · [Getting Started](#-getting-started) · [Security](#-security-first)**

</div>

---

## About

**SecureVault Cloud** is a Python-based command-line project that
helps users generate Terraform configurations for AWS S3 infrastructure
with foundational security controls.

Instead of writing every Terraform resource manually, users can
configure an S3 bucket through an interactive CLI and generate
the corresponding infrastructure configuration.

The project is being developed with a focus on security,
transparency, and beginner-friendly infrastructure workflows.

> **Current scope:** SecureVault generates Terraform configurations
> and supports Terraform initialization and validation. Live AWS
> infrastructure deployment is not currently implemented.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🖥️ Interactive CLI | Configure S3 infrastructure through a terminal interface. |
| ✅ Input Validation | Validate S3 bucket names before generating configurations. |
| ⚙️ Terraform Generation | Generate Terraform files from user-provided configuration. |
| 🔒 Public Access Protection | Configure S3 public-access blocking controls. |
| 🔐 Server-Side Encryption | Configure AES256 encryption at rest. |
| 🗂️ Versioning | Optionally enable S3 bucket versioning. |
| 🛡️ Overwrite Protection | Prevent accidental overwriting of existing Terraform configurations. |
| 🧪 Automated Tests | Test configuration validation, generation, and Terraform command restrictions. |

---

## 🏗️ How It Works

<div align="center">

**User Input**

↓

**SecureVault CLI**

↓

**Configuration Validation**

↓

**Terraform Configuration Generator**

↓

**Generated Terraform Configuration**

↓

**Terraform Initialization & Validation**

</div>

SecureVault separates configuration input, validation, Terraform
generation, and Terraform command execution into individual modules.

This structure makes the application easier to maintain and
provides a foundation for adding further security checks.

---

## 🔐 Security First

Security is a core consideration in the generated S3 configuration.

### Current security controls

- **Public access blocking:** Enables all four S3 public-access blocking settings.
- **Encryption at rest:** Configures AES256 server-side encryption.
- **Optional versioning:** Supports enabling versioning to help recover previous object versions.
- **Input validation:** Rejects invalid bucket names before configuration generation.
- **Overwrite protection:** Avoids replacing an existing generated configuration.
- **Restricted Terraform commands:** The current Terraform manager permits initialization and validation while rejecting `apply` and `destroy`.

### Important limitations

These controls provide a security baseline, not a guarantee of complete security.

- Live AWS deployment and resource inspection are not implemented.
- Generated configurations have not been comprehensively tested against live AWS infrastructure.
- Versioning is not a substitute for independent backups.
- Encryption does not replace appropriate identity and access management.
- Additional controls, such as HTTPS enforcement and automated security auditing, remain potential future improvements.

---

## 🧰 Technology Stack

| Technology | Purpose |
|---|---|
| Python | CLI application and configuration logic |
| Rich | Terminal interface and formatted output |
| Pyfiglet | ASCII-style terminal branding |
| Terraform | Infrastructure configuration and validation |
| AWS | Target cloud platform |
| Amazon S3 | Object storage infrastructure |
| HashiCorp AWS Provider | Terraform integration with AWS |

---

## 🚀 Getting Started

### Prerequisites

Install the following tools before running SecureVault:

- Python 3.10 or newer
- Terraform CLI
- AWS CLI
- Git

Internet access is needed when downloading Terraform providers.

> AWS credentials are not required merely to inspect the source code
> or run the unit tests. Any future live AWS operations will require
> appropriate credentials and permissions.

### 1. Clone the repository

```bash
git clone https://github.com/Shreyash0124/Secure-Vault.git
```

### 2. Enter the project directory

```bash
cd Secure-Vault
```

### 3. Install Python dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Launch SecureVault

```bash
python src/main.py
```

Alternatively, on Windows, run:

```cmd
run_securevault.bat
```

---

## 🧪 Running Tests

Run the automated unit tests from the project root:

```bash
python -m unittest discover -s tests -v
```

The tests cover configuration validation, Terraform generation,
and restrictions on potentially destructive Terraform commands.

The test suite is designed to run without creating AWS resources.

---

## 📁 Project Structure

```text
Secure-Vault/
│
├── src/
│   ├── main.py
│   ├── terminal_ui.py
│   ├── prerequisites.py
│   ├── configuration.py
│   ├── infrastructure_viewer.py
│   ├── terraform_generator.py
│   └── terraform_manager.py
│
├── terraform/
│   ├── main.tf
│   └── .terraform.lock.hcl
│
├── tests/
│   ├── test_configuration.py
│   ├── test_terraform_generator.py
│   └── test_terraform_manager.py
│
├── requirements.txt
├── run_securevault.bat
├── README.md
└── .gitignore
```

The repository structure above describes the intended project files.
Downloaded Terraform providers, Python caches, and locally generated
configurations are excluded from version control.

---

## 🛣️ Development Roadmap

SecureVault Cloud is under active development.

Potential improvements include:

- [ ] Local Terraform security auditing.
- [ ] Detection of missing S3 security controls.
- [ ] HTTPS enforcement checks.
- [ ] More comprehensive automated security tests.
- [ ] Improved configuration diagnostics.
- [ ] Expanded documentation and troubleshooting guidance.
- [ ] Future infrastructure inspection capabilities.

These are planned improvements, not claims about existing functionality.

---

## ⚠️ Development Status

SecureVault Cloud is an experimental project intended for learning
and development.

- Local configuration generation and validation are implemented.
- Automated unit tests are available.
- Live AWS deployment is not implemented.
- Live AWS infrastructure inspection is not implemented.
- No AWS resources have been created by this project.

Review generated Terraform configurations before using them in any
real environment.

---

<div align="center">

**SecureVault Cloud**

*Build securely. Configure confidently.*

</div>