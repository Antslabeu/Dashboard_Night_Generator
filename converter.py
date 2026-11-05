from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from settings import (
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
    EXPECTED_BINARY_SIZE,
    FIT_CONTAIN,
    FIT_COVER,
    FIT_MODES,
    FIT_STRETCH,
)


class ConversionError(Exception):
    """Błąd przygotowania obrazu lub pliku BIN."""


def load_source_image(path: str | Path) -> Image.Image:
    source_path = Path(path)

    if not source_path.is_file():
        raise ConversionError(f"Nie znaleziono pliku: {source_path}")

    try:
        with Image.open(source_path) as opened_image:
            image = ImageOps.exif_transpose(opened_image)
            image.load()
    except (OSError, ValueError) as error:
        raise ConversionError("Nie udało się otworzyć wybranego obrazu.") from error

    return flatten_transparency(image)


def flatten_transparency(image: Image.Image) -> Image.Image:
    """Łączy przezroczysty obraz z białym tłem i zwraca RGB."""
    rgba_image = image.convert("RGBA")
    white_background = Image.new("RGBA", rgba_image.size, "white")
    white_background.alpha_composite(rgba_image)
    return white_background.convert("RGB")


def fit_image(image: Image.Image, fit_mode: str) -> Image.Image:
    """Przygotowuje płótno 800x480 zgodnie z wybranym trybem."""
    if fit_mode not in FIT_MODES:
        raise ConversionError(f"Nieznany sposób dopasowania: {fit_mode}")

    if fit_mode == FIT_STRETCH:
        return image.resize(
            (DISPLAY_WIDTH, DISPLAY_HEIGHT),
            Image.Resampling.LANCZOS,
        )

    if fit_mode == FIT_COVER:
        return ImageOps.fit(
            image,
            (DISPLAY_WIDTH, DISPLAY_HEIGHT),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )

    contained_image = image.copy()
    contained_image.thumbnail(
        (DISPLAY_WIDTH, DISPLAY_HEIGHT),
        Image.Resampling.LANCZOS,
    )

    canvas = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), "white")
    position = (
        (DISPLAY_WIDTH - contained_image.width) // 2,
        (DISPLAY_HEIGHT - contained_image.height) // 2,
    )
    canvas.paste(contained_image, position)
    return canvas


def convert_to_monochrome(
    image: Image.Image,
    threshold: int,
    invert: bool = False,
) -> Image.Image:
    if not 0 <= threshold <= 255:
        raise ConversionError("Próg musi mieścić się w zakresie 0–255.")

    grayscale = image.convert("L")

    if invert:
        grayscale = ImageOps.invert(grayscale)

    return grayscale.point(
        lambda pixel: 255 if pixel > threshold else 0,
        mode="1",
    )


def prepare_image(
    source_image: Image.Image,
    fit_mode: str,
    threshold: int,
    invert: bool = False,
) -> Image.Image:
    fitted_image = fit_image(flatten_transparency(source_image), fit_mode)
    result = convert_to_monochrome(fitted_image, threshold, invert)
    validate_output_image(result)
    return result


def validate_output_image(image: Image.Image) -> None:
    if image.size != (DISPLAY_WIDTH, DISPLAY_HEIGHT):
        raise ConversionError(
            f"Niepoprawne wymiary: {image.width}x{image.height}. "
            f"Oczekiwano {DISPLAY_WIDTH}x{DISPLAY_HEIGHT}."
        )

    if image.mode != "1":
        raise ConversionError(
            f"Niepoprawny tryb obrazu: {image.mode}. Oczekiwano obrazu 1-bitowego."
        )

    binary_data = image.tobytes()
    if len(binary_data) != EXPECTED_BINARY_SIZE:
        raise ConversionError(
            f"Niepoprawny rozmiar bufora: {len(binary_data)} B. "
            f"Oczekiwano {EXPECTED_BINARY_SIZE} B."
        )


def save_outputs(
    image: Image.Image,
    preview_path: str | Path,
    binary_path: str | Path,
) -> tuple[Path, Path]:
    validate_output_image(image)

    preview = Path(preview_path)
    binary = Path(binary_path)
    preview.parent.mkdir(parents=True, exist_ok=True)
    binary.parent.mkdir(parents=True, exist_ok=True)

    image.save(preview, format="PNG")
    binary.write_bytes(image.tobytes())

    if binary.stat().st_size != EXPECTED_BINARY_SIZE:
        raise ConversionError(
            f"Zapisany BIN ma {binary.stat().st_size} B zamiast "
            f"{EXPECTED_BINARY_SIZE} B."
        )

    return preview, binary
