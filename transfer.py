from __future__ import annotations

from pathlib import Path
import subprocess

from settings import (
    EXPECTED_BINARY_SIZE,
    REMOTE_BINARY_NAME,
    REMOTE_OUTPUT_DIRECTORY,
    REMOTE_PREVIEW_NAME,
    SSH_HOST,
    SSH_PORT,
    SSH_USER,
)


class TransferError(Exception):
    """Błąd wysyłania plików do serwera."""


def validate_local_files(preview_path: Path, binary_path: Path) -> None:
    if not preview_path.is_file():
        raise TransferError(f"Nie znaleziono pliku PNG: {preview_path}")

    if not binary_path.is_file():
        raise TransferError(f"Nie znaleziono pliku BIN: {binary_path}")

    binary_size = binary_path.stat().st_size
    if binary_size != EXPECTED_BINARY_SIZE:
        raise TransferError(
            f"Plik BIN ma {binary_size} B zamiast {EXPECTED_BINARY_SIZE} B."
        )


def build_scp_command(local_path: Path, remote_name: str) -> list[str]:
    remote_path = f"{REMOTE_OUTPUT_DIRECTORY}/{remote_name}"
    destination = f"{SSH_USER}@{SSH_HOST}:{remote_path}"

    return [
        "scp",
        "-P",
        str(SSH_PORT),
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        str(local_path),
        destination,
    ]


def _run_scp(command: list[str]) -> None:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise TransferError("Nie znaleziono programu scp w systemie.") from error
    except OSError as error:
        raise TransferError(f"Nie udało się uruchomić SCP: {error}") from error

    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        if not details:
            details = f"SCP zakończyło się kodem {result.returncode}."
        raise TransferError(details)


def upload_dashboard(preview_path: Path, binary_path: Path) -> None:
    """Nadpisuje nightmode.bin i nightmode.png na serwerze."""
    validate_local_files(preview_path, binary_path)

    _run_scp(build_scp_command(binary_path, REMOTE_BINARY_NAME))
    _run_scp(build_scp_command(preview_path, REMOTE_PREVIEW_NAME))
