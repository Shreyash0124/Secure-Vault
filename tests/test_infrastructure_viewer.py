import sys
import tempfile
import unittest

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


# Allow tests to import modules from the src directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from infrastructure_viewer import (
    inspect_configuration,
    view_infrastructure,
)


class TestInspectConfiguration(unittest.TestCase):

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

    def test_inspects_secure_s3_configuration(self):
        self.write_configuration(
            '''
resource "aws_s3_bucket" "securevault" {
  bucket = "securevault-test-123"
}

resource "aws_s3_bucket_public_access_block" "securevault" {
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "securevault" {
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "securevault" {
  versioning_configuration {
    status = "Enabled"
  }
}
'''
        )

        result = inspect_configuration(self.terraform_file)

        self.assertEqual(
            result["bucket_name"],
            "securevault-test-123",
        )
        self.assertEqual(result["encryption"], "AES256")
        self.assertEqual(result["public_access"], "Blocked")
        self.assertEqual(result["versioning"], "Enabled")
        self.assertEqual(result["deployment_status"], "Not verified")
        self.assertEqual(result["file"], self.terraform_file)

    def test_reports_unconfirmed_security_settings(self):
        self.write_configuration(
            '''
resource "aws_s3_bucket" "securevault" {
  bucket = "securevault-test-456"
}
'''
        )

        result = inspect_configuration(self.terraform_file)

        self.assertEqual(
            result["bucket_name"],
            "securevault-test-456",
        )
        self.assertEqual(result["encryption"], "Not confirmed")
        self.assertEqual(result["public_access"], "Not confirmed")
        self.assertEqual(result["versioning"], "Unknown")

    def test_detects_suspended_versioning(self):
        self.write_configuration(
            '''
resource "aws_s3_bucket_versioning" "securevault" {
  versioning_configuration {
    status = "Suspended"
  }
}
'''
        )

        result = inspect_configuration(self.terraform_file)

        self.assertEqual(result["versioning"], "Suspended")

    def test_reports_unknown_bucket_name_when_missing(self):
        self.write_configuration(
            '''
resource "aws_s3_bucket" "example" {
  bucket = "some-other-bucket"
}
'''
        )

        result = inspect_configuration(self.terraform_file)

        self.assertEqual(result["bucket_name"], "Unknown")


class TestViewInfrastructure(unittest.TestCase):

    def test_reports_when_no_generated_directory_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_dir = Path(temp_dir) / "generated"
            output = StringIO()

            with patch(
                "infrastructure_viewer.GENERATED_DIR",
                missing_dir,
            ):
                with redirect_stdout(output):
                    view_infrastructure()

            self.assertIn(
                "No generated configuration directory exists.",
                output.getvalue(),
            )

    def test_reports_when_no_terraform_configurations_exist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            generated_dir = Path(temp_dir)
            output = StringIO()

            with patch(
                "infrastructure_viewer.GENERATED_DIR",
                generated_dir,
            ):
                with redirect_stdout(output):
                    view_infrastructure()

            self.assertIn(
                "No generated Terraform configurations found.",
                output.getvalue(),
            )


if __name__ == "__main__":
    unittest.main()