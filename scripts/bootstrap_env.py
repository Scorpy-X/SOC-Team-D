"""Create the local Python venv and install repo dependencies.

This is the developer bootstrap path. It creates `.venv`, installs Python
requirements, optionally installs frontend npm dependencies, and copies `.env`
from `.env.example` when needed.

Use it from the repo root:

    python scripts/bootstrap_env.py

Optional flags:

    python scripts/bootstrap_env.py --skip-python
    python scripts/bootstrap_env.py --skip-frontend
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import venv
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
VENV_DIR = ROOT_DIR / ".venv"
FRONTEND_DIR = ROOT_DIR / "frontend"
ENV_FILE = ROOT_DIR / ".env"
ENV_EXAMPLE_FILE = ROOT_DIR / ".env.example"


def run_command(command: list[str], *, cwd: Path | None = None) -> None:
    """Run one command and raise if it fails."""

    printable = " ".join(command)
    print(f"\n[run] {printable}")
    subprocess.run(command, cwd=cwd, check=True)


def ensure_env_file() -> None:
    """Create `.env` from `.env.example` when possible."""

    if ENV_FILE.exists():
        print("Using existing .env file.")
        return

    if not ENV_EXAMPLE_FILE.exists():
        print(".env.example was not found. Skipping .env creation.")
        return

    shutil.copyfile(ENV_EXAMPLE_FILE, ENV_FILE)
    print("Created .env from .env.example.")


def ensure_venv() -> Path:
    """Create `.venv` when missing and return the venv Python path."""

    if not VENV_DIR.exists():
        print(f"Creating virtual environment at {VENV_DIR}")
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)
    else:
        print(f"Using existing virtual environment at {VENV_DIR}")

    if os.name == "nt":
        python_path = VENV_DIR / "Scripts" / "python.exe"
    else:
        python_path = VENV_DIR / "bin" / "python"

    if not python_path.exists():
        raise FileNotFoundError(f"Could not find venv Python at {python_path}")

    return python_path


def find_npm() -> str | None:
    """Return the available npm executable name or `None`."""

    for candidate in ("npm.cmd", "npm"):
        resolved = shutil.which(candidate)
        if resolved:
            return candidate
    return None


def get_node_version() -> str | None:
    """Return the Node version string when available."""

    if shutil.which("node") is None:
        return None

    try:
        completed = subprocess.run(
            ["node", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    return completed.stdout.strip() or None


def install_python_requirements() -> None:
    """Create the venv and install the repo Python requirements."""

    ensure_env_file()
    venv_python = ensure_venv()
    run_command([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
    run_command([str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"])
    register_notebook_kernel(venv_python)


def register_notebook_kernel(venv_python: Path) -> None:
    """Register the repo-local notebook kernel for VS Code and Jupyter."""

    kernel_script = ROOT_DIR / "scripts" / "register_repo_kernel.py"
    if not kernel_script.exists():
        print("Notebook kernel script not found. Skipping Jupyter kernel registration.")
        return

    run_command([str(venv_python), str(kernel_script)])


def install_frontend_requirements() -> None:
    """Install frontend packages using the existing lockfile when present."""

    if not FRONTEND_DIR.exists():
        print("Frontend folder not found. Skipping Node dependency install.")
        return

    npm_command = find_npm()
    if npm_command is None:
        print("npm was not found on PATH. Skipping frontend dependency install.")
        return

    node_version = get_node_version()
    if node_version:
        print(f"Detected Node version: {node_version}")

    lockfile = FRONTEND_DIR / "package-lock.json"
    try:
        if lockfile.exists():
            run_command(
                [npm_command, "ci", "--no-audit", "--no-fund"],
                cwd=FRONTEND_DIR,
            )
        else:
            run_command(
                [npm_command, "install", "--no-audit", "--no-fund"],
                cwd=FRONTEND_DIR,
            )
    except subprocess.CalledProcessError as error:
        if lockfile.exists():
            print("\n`npm ci` failed. Retrying once with `npm install`.")
            print("This fallback is mainly for Windows file-lock issues.")
            run_command(
                [npm_command, "install", "--no-audit", "--no-fund"],
                cwd=FRONTEND_DIR,
            )
            return

        print("\nFrontend dependency install failed.")
        print("Common causes in this repo are:")
        print("- Node version below the lockfile requirement")
        print("- Windows/network path issues during npm extraction")
        print("\nRecommended checks:")
        print("- use Node 22.12+ or Node 20.19+")
        print("- use the shorter local repo path under C:\\Users\\ronhu\\projects\\soc-local")
        print("- rerun with: Setup Demo.cmd or python scripts/bootstrap_env.py --skip-python")
        raise error


def print_next_steps(skip_python: bool, skip_frontend: bool) -> None:
    """Print the simplest follow-up commands for the user."""

    print("\nSetup complete.")

    if not skip_frontend and (ROOT_DIR / "Run Demo.cmd").exists():
        print("Start the demo UI with: Run Demo.cmd")

    if not skip_python:
        if os.name == "nt":
            print(r"Activate the Python venv with: .\scripts\Activate-Venv.ps1")
        else:
            print("Activate the Python venv with: source .venv/bin/activate")
        print("Use the notebook kernel named: Python 3.12 (SOC Team D)")
        print("If a live API notebook returns 403, recheck DIMENSION_DEPTHS_API_KEY in .env")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-python",
        action="store_true",
        help="Skip Python virtual environment setup.",
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Skip frontend npm dependency install.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.skip_python and args.skip_frontend:
        print("Nothing to do because both Python and frontend setup were skipped.")
        return 0

    os.chdir(ROOT_DIR)

    if not args.skip_python:
        install_python_requirements()

    if not args.skip_frontend:
        install_frontend_requirements()

    print_next_steps(args.skip_python, args.skip_frontend)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
