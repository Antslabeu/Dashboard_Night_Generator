from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from settings import EXPECTED_BINARY_SIZE
from transfer import (
    TransferError,
    build_scp_command,
    upload_dashboard,
    validate_local_files,
)


class TransferTests(unittest.TestCase):
    def test_command_uses_configured_server_and_remote_name(self) -> None:
        command = build_scp_command(Path("/tmp/source.bin"), "nightmode.bin")

        self.assertEqual(command[0], "scp")
        self.assertIn("22", command)
        self.assertEqual(command[-1], (
            "zuczek@192.168.100.121:"
            "/home/zuczek/dashboard/output/nightmode.bin"
        ))

    def test_validation_rejects_invalid_binary_size(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            preview = directory / "preview.png"
            binary = directory / "image.bin"
            preview.write_bytes(b"png")
            binary.write_bytes(b"invalid")

            with self.assertRaises(TransferError):
                validate_local_files(preview, binary)

    @patch("transfer._run_scp")
    def test_upload_sends_bin_and_png_with_fixed_names(self, run_scp) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            preview = directory / "local_preview.png"
            binary = directory / "local_image.bin"
            preview.write_bytes(b"png")
            binary.write_bytes(b"\xff" * EXPECTED_BINARY_SIZE)

            upload_dashboard(preview, binary)

        self.assertEqual(run_scp.call_count, 2)
        self.assertTrue(run_scp.call_args_list[0].args[0][-1].endswith(
            "/nightmode.bin"
        ))
        self.assertTrue(run_scp.call_args_list[1].args[0][-1].endswith(
            "/nightmode.png"
        ))


if __name__ == "__main__":
    unittest.main()
