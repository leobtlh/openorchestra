"""Helpers for probing external command-line tools."""

import subprocess

INSTALL_CHECK_TIMEOUT_SECONDS = 10


def executable_available(
    command: str,
    args: tuple[str, ...] = ("--version",),
    timeout: int = INSTALL_CHECK_TIMEOUT_SECONDS,
) -> bool:
    """Return True when ``command`` runs successfully with ``args``."""
    try:
        result = subprocess.run(
            [command, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0
