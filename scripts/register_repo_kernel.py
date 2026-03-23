"""Register the repo-local Jupyter kernel for SOC Team D."""

from __future__ import annotations

import subprocess
import sys


KERNEL_NAME = "soc-team-d-py312"
DISPLAY_NAME = f"Python {sys.version_info.major}.{sys.version_info.minor} (SOC Team D)"


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "ipykernel",
        "install",
        "--user",
        "--name",
        KERNEL_NAME,
        "--display-name",
        DISPLAY_NAME,
    ]
    subprocess.run(command, check=True)
    print(f"Registered notebook kernel: {DISPLAY_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
