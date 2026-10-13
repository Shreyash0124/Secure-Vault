import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import terraform_generator


class TestTerraformGenerator(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.generated_dir = Path(self.temp_dir.name) / "generated"
        self.configuration = {
            "bucket_name": "securevault-demo-123",
            "versioning": True,
        }
        self.directory_patch = patch.object(
            terraform_generator,
            "GENERATED_DIR",
            self.generated_dir,
        )
        self.directory_patch.start()

    def tearDown(self):
        self.directory_patch.stop()
        self.temp_dir.cleanup()

    def test_generates_terraform_file(self):
        output_file = terraform_generator.generate_terraform(self.configuration)
        self.assertTrue(output_file.is_file())
        self.assertEqual(output_file.name, "main.tf")
        self.assertEqual(
            output_file.parent,
            self.generated_dir / "securevault-demo-123",
        )

    def test_generated_configuration_contains_bucket_name(self):
        output_file = terraform_generator.generate_terraform(self.configuration)
        content = output_file.read_text(encoding="utf-8")
        self.assertIn('bucket = "securevault-demo-123"', content)

    def test_generated_configuration_enables_encryption(self):
        output_file = terraform_generator.generate_terraform(self.configuration)
        content = output_file.read_text(encoding="utf-8")
        self.assertIn('sse_algorithm = "AES256"', content)

    def test_versioning_enabled_generates_enabled_resource(self):
        output = terraform_generator.render_terraform({
            "bucket_name": "securevault-versioning-on",
            "versioning": True,
            "encryption": "AES256",
        })
        self.assertIn('resource "aws_s3_bucket_versioning" "securevault"', output)
        self.assertIn('status = "Enabled"', output)

    def test_versioning_disabled_omits_versioning_resource(self):
        output = terraform_generator.render_terraform({
            "bucket_name": "securevault-versioning-off",
            "versioning": False,
            "encryption": "AES256",
        })
        self.assertNotIn('resource "aws_s3_bucket_versioning" "securevault"', output)
        self.assertNotIn('status = "Suspended"', output)

    def test_customer_managed_kms_includes_key_arn(self):
        key_arn = (
            "arn:aws:kms:ap-south-1:123456789012:"
            "key/12345678-1234-1234-1234-123456789012"
        )
        output = terraform_generator.render_terraform({
            "bucket_name": "securevault-kms-customer",
            "versioning": True,
            "encryption": "aws:kms-customer",
            "kms_key_arn": key_arn,
        })
        self.assertIn('sse_algorithm = "aws:kms"', output)
        self.assertIn(f'kms_master_key_id = "{key_arn}"', output)

    def test_existing_configuration_is_not_overwritten(self):
        output_dir = self.generated_dir / self.configuration["bucket_name"]
        output_dir.mkdir(parents=True)
        existing_file = output_dir / "main.tf"
        original_content = "# Existing configuration\n"
        existing_file.write_text(original_content, encoding="utf-8")

        with self.assertRaises(FileExistsError):
            terraform_generator.generate_terraform(self.configuration)

        self.assertEqual(
            existing_file.read_text(encoding="utf-8"),
            original_content,
        )

    def test_invalid_bucket_name_is_rejected(self):
        invalid_configuration = {
            "bucket_name": "INVALID_NAME",
            "versioning": True,
        }
        with self.assertRaises(ValueError):
            terraform_generator.generate_terraform(invalid_configuration)


if __name__ == "__main__":
    unittest.main(verbosity=2)
