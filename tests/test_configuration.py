import sys
import unittest
from pathlib import Path

# Add the src directory to Python's import path.
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from configuration import validate_bucket_name


class TestBucketNameValidation(unittest.TestCase):

    def test_valid_bucket_name(self):
        valid, _ = validate_bucket_name("securevault-demo-123")
        self.assertTrue(valid)

    def test_uppercase_is_rejected(self):
        valid, _ = validate_bucket_name("SecureVaultDemo")
        self.assertFalse(valid)

    def test_underscore_is_rejected(self):
        valid, _ = validate_bucket_name("secure_vault")
        self.assertFalse(valid)

    def test_name_too_short_is_rejected(self):
        valid, _ = validate_bucket_name("ab")
        self.assertFalse(valid)

    def test_leading_hyphen_is_rejected(self):
        valid, _ = validate_bucket_name("-securevault")
        self.assertFalse(valid)

    def test_trailing_hyphen_is_rejected(self):
        valid, _ = validate_bucket_name("securevault-")
        self.assertFalse(valid)

    def test_consecutive_periods_are_rejected(self):
        valid, _ = validate_bucket_name("securevault..demo")
        self.assertFalse(valid)

    def test_ip_address_format_is_rejected(self):
        valid, _ = validate_bucket_name("192.168.1.1")
        self.assertFalse(valid)


if __name__ == "__main__":
    unittest.main(verbosity=2)