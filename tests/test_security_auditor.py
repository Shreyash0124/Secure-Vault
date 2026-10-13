import sys
import tempfile
import unittest

from pathlib import Path


# Allow tests to import modules from src.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from security_auditor import audit_terraform


class TestSecurityAuditor(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.terraform_file = Path(self.temp_dir.name) / "main.tf"

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_configuration(self, content):
        self.terraform_file.write_text(
            content,
            encoding="utf-8",
        )

    def get_finding(self, result, rule):
        for finding in result["findings"]:
            if finding["security_rule"] == rule:
                return finding

        self.fail(f"Security rule not found: {rule}")

    def test_secure_configuration_passes_all_checks(self):
        self.write_configuration(
            '''
resource "aws_s3_bucket" "securevault" {
  bucket = "securevault-demo-123"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "securevault" {
  bucket = aws_s3_bucket.securevault.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "securevault" {
  bucket = aws_s3_bucket.securevault.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "securevault" {
  bucket = aws_s3_bucket.securevault.id

  versioning_configuration {
    status = "Enabled"
  }
}
'''
        )

        result = audit_terraform(self.terraform_file)

        self.assertEqual(
            result["bucket_name"],
            "securevault-demo-123",
        )

        self.assertEqual(len(result["findings"]), 3)

        for finding in result["findings"]:
            self.assertTrue(finding["verdict"].startswith("PASS"))

    def test_missing_encryption_is_a_failure(self):
        self.write_configuration(
            '''
resource "aws_s3_bucket" "securevault" {
  bucket = "securevault-demo-123"
}
'''
        )

        result = audit_terraform(self.terraform_file)
        finding = self.get_finding(result, "Server-Side Encryption")

        self.assertEqual(finding["status"], "Not found")
        self.assertEqual(finding["severity"], "HIGH")
        self.assertTrue(finding["verdict"].startswith("FAIL"))

    def test_missing_public_access_block_is_critical(self):
        self.write_configuration(
            '''
resource "aws_s3_bucket" "securevault" {
  bucket = "securevault-demo-123"
}
'''
        )

        result = audit_terraform(self.terraform_file)
        finding = self.get_finding(result, "S3 Access Protection")

        self.assertEqual(finding["severity"], "CRITICAL")
        self.assertTrue(finding["verdict"].startswith("FAIL"))

    def test_incomplete_public_access_block_is_unknown(self):
        self.write_configuration(
            '''
resource "aws_s3_bucket_public_access_block" "securevault" {
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
}
'''
        )

        result = audit_terraform(self.terraform_file)
        finding = self.get_finding(result, "S3 Access Protection")

        self.assertEqual(finding["status"], "Incomplete")
        self.assertTrue(finding["verdict"].startswith("UNKNOWN"))

    def test_explicitly_false_public_access_setting_fails(self):
        self.write_configuration(
            '''
resource "aws_s3_bucket_public_access_block" "securevault" {
  block_public_acls       = true
  block_public_policy     = false
  ignore_public_acls      = true
  restrict_public_buckets = true
}
'''
        )

        result = audit_terraform(self.terraform_file)
        finding = self.get_finding(result, "S3 Access Protection")

        self.assertEqual(finding["severity"], "CRITICAL")
        self.assertTrue(finding["verdict"].startswith("FAIL"))

    def test_suspended_versioning_produces_warning(self):
        self.write_configuration(
            '''
resource "aws_s3_bucket_versioning" "securevault" {
  versioning_configuration {
    status = "Suspended"
  }
}
'''
        )

        result = audit_terraform(self.terraform_file)
        finding = self.get_finding(result, "Bucket Versioning")

        self.assertEqual(finding["status"], "Suspended")
        self.assertEqual(finding["severity"], "MEDIUM")
        self.assertTrue(finding["verdict"].startswith("WARN"))

    def test_missing_versioning_produces_warning(self):
        self.write_configuration(
            '''
resource "aws_s3_bucket" "securevault" {
  bucket = "securevault-demo-123"
}
'''
        )

        result = audit_terraform(self.terraform_file)
        finding = self.get_finding(result, "Bucket Versioning")

        self.assertEqual(finding["status"], "Not found")
        self.assertTrue(finding["verdict"].startswith("WARN"))

    def test_missing_bucket_name_is_reported_as_unknown(self):
        self.write_configuration(
            '''
resource "aws_s3_bucket" "securevault" {
  bucket = var.bucket_name
}
'''
        )

        result = audit_terraform(self.terraform_file)

        self.assertEqual(result["bucket_name"], "Unknown")

    def test_findings_are_sorted_by_severity(self):
        self.write_configuration(
            '''
resource "aws_s3_bucket" "securevault" {
  bucket = "securevault-demo-123"
}

resource "aws_s3_bucket_versioning" "securevault" {
  versioning_configuration {
    status = "Suspended"
  }
}
'''
        )

        result = audit_terraform(self.terraform_file)

        severities = [
            finding["severity"]
            for finding in result["findings"]
        ]

        severity_order = {
            "CRITICAL": 0,
            "HIGH": 1,
            "MEDIUM": 2,
            "LOW": 3,
            "INFO": 4,
        }

        self.assertEqual(
            severities,
            sorted(severities, key=severity_order.get),
        )

    def test_audit_does_not_claim_live_deployment_status(self):
        self.write_configuration(
            '''
resource "aws_s3_bucket" "securevault" {
  bucket = "securevault-demo-123"
}
'''
        )

        result = audit_terraform(self.terraform_file)

        self.assertEqual(
            result["deployment_status"],
            "Not verified",
        )

    def test_wrong_bucket_reference_is_unknown(self):
        self.write_configuration("""
resource "aws_s3_bucket" "securevault" {
  bucket = "securevault-demo-123"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "securevault" {
  bucket = aws_s3_bucket.nonexistent.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
""")
        result = audit_terraform(self.terraform_file)
        finding = self.get_finding(result, "Server-Side Encryption")

        self.assertTrue(finding["verdict"].startswith("UNKNOWN"))

    def test_missing_bucket_does_not_pass_access_protection(self):
        self.write_configuration("""
resource "aws_s3_bucket_public_access_block" "securevault" {
  bucket = aws_s3_bucket.securevault.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
""")
        result = audit_terraform(self.terraform_file)
        finding = self.get_finding(result, "S3 Access Protection")

        self.assertTrue(finding["verdict"].startswith("UNKNOWN"))

    def test_multiple_buckets_are_reported_as_ambiguous(self):
        self.write_configuration("""
resource "aws_s3_bucket" "first" {
  bucket = "securevault-first-123"
}

resource "aws_s3_bucket" "second" {
  bucket = "securevault-second-123"
}
""")
        result = audit_terraform(self.terraform_file)
        finding = self.get_finding(result, "S3 Bucket Resource")

        self.assertEqual(finding["status"], "Ambiguous")
        self.assertTrue(finding["verdict"].startswith("UNKNOWN"))

if __name__ == "__main__":
    unittest.main()
