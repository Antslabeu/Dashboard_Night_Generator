from pathlib import Path
import tempfile
import unittest

from PIL import Image

from converter import prepare_image, save_outputs
from settings import (
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
    EXPECTED_BINARY_SIZE,
    FIT_CONTAIN,
    FIT_COVER,
    FIT_STRETCH,
)


class ConverterTests(unittest.TestCase):
    def test_all_fit_modes_create_expected_image(self) -> None:
        source = Image.new("RGB", (320, 200), "black")

        for fit_mode in (FIT_CONTAIN, FIT_COVER, FIT_STRETCH):
            with self.subTest(fit_mode=fit_mode):
                result = prepare_image(source, fit_mode, 128)
                self.assertEqual(result.size, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
                self.assertEqual(result.mode, "1")
                self.assertEqual(len(result.tobytes()), EXPECTED_BINARY_SIZE)

    def test_white_image_produces_ff_bytes(self) -> None:
        source = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), "white")
        result = prepare_image(source, FIT_STRETCH, 128)
        self.assertEqual(set(result.tobytes()), {0xFF})

    def test_black_image_produces_zero_bytes(self) -> None:
        source = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), "black")
        result = prepare_image(source, FIT_STRETCH, 128)
        self.assertEqual(set(result.tobytes()), {0x00})

    def test_invert_reverses_pixels(self) -> None:
        source = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), "white")
        result = prepare_image(source, FIT_STRETCH, 128, invert=True)
        self.assertEqual(set(result.tobytes()), {0x00})

    def test_save_outputs_creates_48000_byte_binary(self) -> None:
        source = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), "white")
        result = prepare_image(source, FIT_STRETCH, 128)

        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            preview_path, binary_path = save_outputs(
                result,
                directory / "preview.png",
                directory / "image.bin",
            )

            self.assertTrue(preview_path.is_file())
            self.assertEqual(binary_path.stat().st_size, EXPECTED_BINARY_SIZE)


if __name__ == "__main__":
    unittest.main()
