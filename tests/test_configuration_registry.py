"""Isolated unit tests for SecureVault's local configuration registry."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

import configuration_registry as registry


class TestConfigurationRegistry(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.generated_dir = self.root / "generated"
        self.generated_dir.mkdir()
        self.project_root = self.root
        self.tf_file = self.generated_dir / "demo-bucket" / "main.tf"
        self.tf_file.parent.mkdir(parents=True)
        self.tf_file.write_text('# test-only Terraform configuration\n', encoding="utf-8")

        self.patches = [
            patch.object(registry, "GENERATED_DIR", self.generated_dir),
            patch.object(registry, "PROJECT_ROOT", self.project_root),
            patch.object(registry, "REGISTRY_FILE", self.generated_dir / ".securevault_registry.json"),
            patch.object(registry, "inspect_configuration", return_value={
                "bucket_name": "demo-bucket",
                "encryption": "SSE-S3",
                "versioning": "Enabled",
                "public_access": "All protections enabled",
            }),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_records_configuration_metadata(self):
        record = registry.record_configuration(self.tf_file)
        self.assertEqual(record["bucket_name"], "demo-bucket")
        self.assertEqual(record["encryption"], "SSE-S3")
        self.assertEqual(record["versioning"], "Enabled")
        self.assertIsNone(record["latest_audit"])
        self.assertTrue(record["generated_at"])
        self.assertTrue(registry.REGISTRY_FILE.is_file())

    def test_refresh_preserves_original_creation_timestamp(self):
        first = registry.record_configuration(self.tf_file)
        second = registry.record_configuration(self.tf_file)
        self.assertEqual(first["generated_at"], second["generated_at"])

    def test_records_latest_audit_and_timestamp(self):
        report = {"overall_result": "PASS", "finding_count": 2}
        record = registry.record_audit(self.tf_file, report)
        self.assertEqual(record["latest_audit"]["overall_result"], "PASS")
        self.assertEqual(record["latest_audit"]["finding_count"], 2)
        self.assertTrue(record["latest_audit"]["audited_at"])

    def test_loads_persisted_registry_between_calls(self):
        registry.record_configuration(self.tf_file)
        loaded = json.loads(registry.REGISTRY_FILE.read_text(encoding="utf-8"))
        self.assertEqual(len(loaded), 1)
        self.assertEqual(next(iter(loaded.values()))["bucket_name"], "demo-bucket")

    def test_lists_existing_generated_configurations(self):
        registry.record_configuration(self.tf_file)
        records = registry.list_configuration_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["bucket_name"], "demo-bucket")

    def test_missing_registry_starts_empty(self):
        self.assertEqual(registry._load(), {})

    def test_corrupt_registry_does_not_crash(self):
        registry.REGISTRY_FILE.write_text("not-json", encoding="utf-8")
        self.assertEqual(registry._load(), {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
