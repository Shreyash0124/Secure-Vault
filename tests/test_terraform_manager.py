import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import terraform_manager


class TestTerraformManagerSafety(unittest.TestCase):

    def test_apply_command_is_rejected(self):
        with patch.object(
            terraform_manager.subprocess,
            "run",
        ) as mock_run:
            result = terraform_manager.run_terraform_command(["apply"])

        self.assertFalse(result)
        mock_run.assert_not_called()

    def test_destroy_command_is_rejected(self):
        with patch.object(
            terraform_manager.subprocess,
            "run",
        ) as mock_run:
            result = terraform_manager.run_terraform_command(["destroy"])

        self.assertFalse(result)
        mock_run.assert_not_called()

    def test_unexpected_arguments_are_rejected(self):
        with patch.object(
            terraform_manager.subprocess,
            "run",
        ) as mock_run:
            result = terraform_manager.run_terraform_command(
                ["validate", "-var-file=unexpected.tfvars"]
            )

        self.assertFalse(result)
        mock_run.assert_not_called()

    def test_empty_command_is_rejected(self):
        with patch.object(
            terraform_manager.subprocess,
            "run",
        ) as mock_run:
            result = terraform_manager.run_terraform_command([])

        self.assertFalse(result)
        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)